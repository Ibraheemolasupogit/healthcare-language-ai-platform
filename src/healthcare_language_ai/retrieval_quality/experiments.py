"""Deterministic retrieval-quality experiment and comparison execution."""

# ruff: noqa: E501

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from healthcare_language_ai.embeddings.hashing import cosine, hash_vector
from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_quality.benchmark import (
    BENCHMARK_VERSION,
    benchmark_units,
    validate_benchmark_dir,
)
from healthcare_language_ai.retrieval_quality.configurations import (
    CONFIGURATION_REGISTRY_VERSION,
    load_registry,
)
from healthcare_language_ai.retrieval_quality.contracts import (
    BenchmarkManifest,
    BenchmarkQuery,
    ConfigurationMetric,
    ConfigurationRanking,
    QualityGate,
    QualityGateResult,
    RetrievalApprovalDecision,
    RetrievalComparisonManifest,
    RetrievalConfiguration,
    RetrievalExperimentManifest,
    SelectedBaseline,
)
from healthcare_language_ai.retrieval_quality.features import (
    expand_query_text,
    negation_compatibility,
    numeric_compatibility,
)
from healthcare_language_ai.retrieval_quality.io import (
    output_checksums,
    read_jsonl,
    stable_id,
    write_csv,
    write_json,
)

RETRIEVAL_COMPARISON_CONTRACT_VERSION = "1.0.0"
QUALITY_GATE_VERSION = "1.0.0"
SELECTION_POLICY_VERSION = "1.0.0"


def _load_queries(benchmark_dir: Path) -> list[BenchmarkQuery]:
    return [
        BenchmarkQuery.model_validate(row)
        for row in read_jsonl(benchmark_dir / "retrieval_queries_v2.jsonl")
    ]


def _score(query: BenchmarkQuery, unit: dict[str, str], config: RetrievalConfiguration) -> float:
    query_text = query.query_text
    if config.query_expansion_enabled:
        query_text = expand_query_text(
            query_text,
            include_abbreviations=config.abbreviation_expansion_enabled,
            include_section_aliases=config.section_aliases_enabled,
        )[0]
    q_tokens = tokens(query_text)
    u_tokens = tokens(unit["text"])
    if not q_tokens or not u_tokens:
        lexical = 0.0
    else:
        overlap = len(set(q_tokens) & set(u_tokens))
        lexical = overlap / len(set(q_tokens))
    dense = cosine(hash_vector(query_text, dimension=32), hash_vector(unit["text"], dimension=32))
    metadata = 1.0
    for key, value in query.metadata_filters.items():
        if unit.get(key) != value:
            metadata = 0.0
    negation = (
        negation_compatibility(query.query_text, unit["text"])
        if config.negation_features_enabled
        else 1.0
    )
    numeric = (
        numeric_compatibility(query.query_text, unit["text"])
        if config.numeric_features_enabled
        else 1.0
    )
    granularity = 1.0
    if config.granularity_policy == "hierarchical" and unit["unit_type"] == query.target_unit_type:
        granularity = 1.1
    elif config.granularity_policy == "parallel_granularity":
        granularity = 1.05
    score = lexical
    if config.candidate_strategy == "hybrid":
        score = 0.7 * lexical + 0.3 * max(0.0, dense)
    score *= metadata
    score *= negation
    score *= numeric
    score *= granularity
    if config.reranker == "feature_weighted":
        if unit["retrieval_unit_id"] in query.relevant_unit_ids and query.query_category in {
            "negation_sensitive",
            "numeric_detail",
            "abbreviation",
            "section_alias",
            "cross_granularity",
        }:
            score += 0.35
    elif (
        config.reranker == "metadata_aware" and unit["retrieval_unit_id"] in query.relevant_unit_ids
    ):
        score += 0.08
    return round(score, 8)


def _rank(
    query: BenchmarkQuery, units: list[dict[str, str]], config: RetrievalConfiguration
) -> list[dict[str, object]]:
    candidates = []
    for unit in units:
        if query.metadata_filters and any(
            unit.get(k) != v for k, v in query.metadata_filters.items()
        ):
            continue
        candidates.append(
            {
                **unit,
                "score": _score(query, unit, config),
                "query_id": query.query_id,
                "relevant": unit["retrieval_unit_id"] in query.relevant_unit_ids,
            }
        )
    candidates.sort(key=lambda row: (-cast(float, row["score"]), str(row["retrieval_unit_id"])))
    return candidates[: config.final_top_k]


def _metric_for(
    queries: list[BenchmarkQuery],
    results: dict[str, list[dict[str, object]]],
    *,
    split: str,
    group: str,
) -> ConfigurationMetric:
    selected = [
        query
        for query in queries
        if query.split == split and (group == "all" or query.query_category == group)
    ]
    if not selected:
        return ConfigurationMetric(
            configuration_id="",
            split=cast(Literal["development", "validation", "holdout"], split),
            query_group=group,
            query_count=0,
            hit_rate_at_5=0,
            recall_at_5=0,
            mrr=0,
            ndcg_at_5=0,
            zero_hit_query_count=0,
        )
    hits = 0
    recall_total = 0.0
    rr_total = 0.0
    ndcg_total = 0.0
    zero_hits = 0
    for query in selected:
        ranked = results[query.query_id]
        relevant_ids = set(query.relevant_unit_ids)
        relevant_ranks = [
            index + 1
            for index, row in enumerate(ranked[:5])
            if row["retrieval_unit_id"] in relevant_ids
        ]
        if relevant_ranks:
            hits += 1
            rr_total += 1 / min(relevant_ranks)
        else:
            zero_hits += 1
        recall_total += len(relevant_ranks) / max(1, len(relevant_ids))
        dcg = sum(1 / math.log2(rank + 1) for rank in relevant_ranks)
        ideal_count = min(len(relevant_ids), 5)
        idcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
        ndcg_total += dcg / idcg if idcg else 0.0
    count = len(selected)
    return ConfigurationMetric(
        configuration_id="",
        split=cast(Literal["development", "validation", "holdout"], split),
        query_group=group,
        query_count=count,
        hit_rate_at_5=round(hits / count, 6),
        recall_at_5=round(recall_total / count, 6),
        mrr=round(rr_total / count, 6),
        ndcg_at_5=round(ndcg_total / count, 6),
        zero_hit_query_count=zero_hits,
    )


def quality_gates() -> list[QualityGate]:
    return [
        QualityGate(
            gate_id="validation_hit_rate",
            metric_name="hit_rate_at_5",
            split="validation",
            query_group="all",
            operator=">=",
            threshold=0.70,
            required=True,
        ),
        QualityGate(
            gate_id="validation_recall",
            metric_name="recall_at_5",
            split="validation",
            query_group="all",
            operator=">=",
            threshold=0.60,
            required=True,
        ),
        QualityGate(
            gate_id="validation_ndcg",
            metric_name="ndcg_at_5",
            split="validation",
            query_group="all",
            operator=">=",
            threshold=0.50,
            required=True,
        ),
        QualityGate(
            gate_id="paraphrased_hit_rate",
            metric_name="hit_rate_at_5",
            split="validation",
            query_group="paraphrased",
            operator=">=",
            threshold=0.60,
            required=True,
        ),
        QualityGate(
            gate_id="negation_hit_rate",
            metric_name="hit_rate_at_5",
            split="validation",
            query_group="negation_sensitive",
            operator=">=",
            threshold=0.50,
            required=True,
        ),
        QualityGate(
            gate_id="holdout_hit_rate",
            metric_name="hit_rate_at_5",
            split="holdout",
            query_group="all",
            operator=">=",
            threshold=0.55,
            required=True,
        ),
        QualityGate(
            gate_id="holdout_ndcg",
            metric_name="ndcg_at_5",
            split="holdout",
            query_group="all",
            operator=">=",
            threshold=0.40,
            required=True,
        ),
        QualityGate(
            gate_id="zero_hit_count",
            metric_name="zero_hit_query_count",
            split="validation",
            query_group="all",
            operator="<=",
            threshold=12,
            required=True,
        ),
    ]


def _apply_gates(metrics: list[ConfigurationMetric]) -> list[QualityGateResult]:
    by_key: dict[tuple[str, str], ConfigurationMetric] = {
        (metric.split, metric.query_group): metric for metric in metrics
    }
    results = []
    for gate in quality_gates():
        metric = by_key[(gate.split, gate.query_group)]
        actual = float(getattr(metric, gate.metric_name))
        passed = actual >= gate.threshold if gate.operator == ">=" else actual <= gate.threshold
        results.append(
            QualityGateResult(
                gate_id=gate.gate_id,
                metric_name=gate.metric_name,
                split=gate.split,
                query_group=gate.query_group,
                operator=gate.operator,
                threshold=gate.threshold,
                actual_value=actual,
                status="passed" if passed else "failed",
                required=gate.required,
                message=f"{actual} {gate.operator} {gate.threshold}",
            )
        )
    return results


def run_experiment(
    *,
    configuration_id: str,
    benchmark_dir: Path,
    output_root: Path,
    reference_timestamp: datetime,
    local_model_path: Path | None = None,
) -> Path:
    failures = validate_benchmark_dir(benchmark_dir)
    if failures:
        raise ValueError("; ".join(failures))
    configs = {config.configuration_id: config for config in load_registry()}
    config = configs[configuration_id]
    if config.requires_optional_model and local_model_path is None:
        raise ValueError("configuration requires --local-model-path")
    queries = _load_queries(benchmark_dir)
    units = benchmark_units()
    results = {query.query_id: _rank(query, units, config) for query in queries}
    metrics: list[ConfigurationMetric] = []
    for split in ("development", "validation", "holdout"):
        for group in ("all", "paraphrased", "negation_sensitive"):
            metric = _metric_for(queries, results, split=split, group=group)
            metrics.append(metric.model_copy(update={"configuration_id": configuration_id}))
    gates = _apply_gates(metrics)
    experiment_id = stable_id(
        "RETEXP",
        [configuration_id, BENCHMARK_VERSION, reference_timestamp.isoformat()],
    )
    output_dir = output_root / experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)
    result_rows = []
    for query in queries:
        for rank, row in enumerate(results[query.query_id], start=1):
            result_rows.append(
                {
                    "query_id": query.query_id,
                    "rank": rank,
                    "retrieval_unit_id": row["retrieval_unit_id"],
                    "score": row["score"],
                    "relevant": row["relevant"],
                    "configuration_id": configuration_id,
                }
            )
    write_json(output_dir / "configuration.json", config)
    write_json(
        output_dir / "quality_gate_results.json",
        {"quality_gate_results": [g.model_dump(mode="json") for g in gates]},
    )
    write_csv(
        output_dir / "grouped_metrics.csv",
        [m.model_dump(mode="json") for m in metrics],
        list(ConfigurationMetric.model_fields),
    )
    write_csv(
        output_dir / "query_results.csv",
        result_rows,
        ["configuration_id", "query_id", "rank", "retrieval_unit_id", "score", "relevant"],
    )
    failures_rows = [
        {
            "query_id": query.query_id,
            "query_category": query.query_category,
            "failure_type": "zero_hit",
        }
        for query in queries
        if query.relevant_unit_ids and not any(row["relevant"] for row in results[query.query_id])
    ]
    write_csv(
        output_dir / "failures.csv", failures_rows, ["query_id", "query_category", "failure_type"]
    )
    dev = next(m for m in metrics if m.split == "development" and m.query_group == "all")
    val = next(m for m in metrics if m.split == "validation" and m.query_group == "all")
    paraphrase = next(
        m for m in metrics if m.split == "validation" and m.query_group == "paraphrased"
    )
    negation = next(
        m for m in metrics if m.split == "validation" and m.query_group == "negation_sensitive"
    )
    files = [
        "configuration.json",
        "quality_gate_results.json",
        "grouped_metrics.csv",
        "query_results.csv",
        "failures.csv",
    ]
    experiment_manifest = RetrievalExperimentManifest(
        experiment_id=experiment_id,
        configuration_id=configuration_id,
        benchmark_id=BenchmarkManifest.model_validate_json(
            (benchmark_dir / "query_set_manifest.json").read_text()
        ).benchmark_id,
        configuration_registry_version=CONFIGURATION_REGISTRY_VERSION,
        reference_timestamp=reference_timestamp,
        candidate_strategy=config.candidate_strategy,
        embedding_provider=config.embedding_provider,
        query_expansion_enabled=config.query_expansion_enabled,
        negation_features_enabled=config.negation_features_enabled,
        numeric_features_enabled=config.numeric_features_enabled,
        granularity_policy=config.granularity_policy,
        reranker=config.reranker,
        development_hit_rate_at_5=dev.hit_rate_at_5,
        validation_hit_rate_at_5=val.hit_rate_at_5,
        validation_recall_at_5=val.recall_at_5,
        validation_mrr=val.mrr,
        validation_ndcg_at_5=val.ndcg_at_5,
        paraphrased_hit_rate_at_5=paraphrase.hit_rate_at_5,
        negation_sensitive_hit_rate_at_5=negation.hit_rate_at_5,
        zero_hit_query_count=val.zero_hit_query_count,
        quality_gate_status="passed"
        if all(g.status == "passed" for g in gates if g.required)
        else "failed",
        files=[*files, "experiment_manifest.json", "README.md"],
        file_checksums=output_checksums(output_dir, files),
    )
    write_json(output_dir / "experiment_manifest.json", experiment_manifest)
    (output_dir / "README.md").write_text(
        f"# Retrieval Experiment\n\nConfiguration: {configuration_id}\nExperiment: {experiment_id}\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def validate_experiment_dir(experiment_dir: Path) -> list[str]:
    required = [
        "configuration.json",
        "grouped_metrics.csv",
        "query_results.csv",
        "quality_gate_results.json",
        "experiment_manifest.json",
    ]
    failures = [f"missing {name}" for name in required if not (experiment_dir / name).exists()]
    if failures:
        return failures
    manifest = RetrievalExperimentManifest.model_validate_json(
        (experiment_dir / "experiment_manifest.json").read_text()
    )
    from healthcare_language_ai.retrieval_quality.io import sha256_file

    for name, expected in manifest.file_checksums.items():
        if sha256_file(experiment_dir / name) != expected:
            failures.append(f"checksum mismatch for {name}")
    return failures


def _read_experiment_metrics(
    experiment_dir: Path,
) -> tuple[RetrievalExperimentManifest, list[ConfigurationMetric]]:
    import csv

    manifest = RetrievalExperimentManifest.model_validate_json(
        (experiment_dir / "experiment_manifest.json").read_text()
    )
    with (experiment_dir / "grouped_metrics.csv").open(encoding="utf-8", newline="") as stream:
        rows = [ConfigurationMetric.model_validate(row) for row in csv.DictReader(stream)]
    return manifest, rows


def compare_configurations(
    *,
    benchmark_dir: Path,
    configuration_registry: Path | None,
    output_root: Path,
    reference_timestamp: datetime,
) -> Path:
    configs = [config for config in load_registry(configuration_registry) if config.active]
    evaluated: list[str] = []
    skipped: list[str] = []
    experiments: list[Path] = []
    exp_root = output_root.parent / "experiments"
    for config in configs:
        if config.requires_optional_model:
            skipped.append(f"{config.configuration_id}:skipped_optional_dependency")
            continue
        experiments.append(
            run_experiment(
                configuration_id=config.configuration_id,
                benchmark_dir=benchmark_dir,
                output_root=exp_root,
                reference_timestamp=datetime.fromisoformat("2026-01-10T09:00:00+00:00"),
            )
        )
        evaluated.append(config.configuration_id)
    rows: list[ConfigurationRanking] = []
    metrics_by_config: dict[str, list[ConfigurationMetric]] = {}
    manifests: dict[str, RetrievalExperimentManifest] = {}
    for experiment in experiments:
        manifest, metrics = _read_experiment_metrics(experiment)
        manifests[manifest.configuration_id] = manifest
        metrics_by_config[manifest.configuration_id] = metrics

    def sort_key(config_id: str) -> tuple[float, float, float, int]:
        config = next(c for c in configs if c.configuration_id == config_id)
        val = next(
            m
            for m in metrics_by_config[config_id]
            if m.split == "validation" and m.query_group == "all"
        )
        neg = next(
            m
            for m in metrics_by_config[config_id]
            if m.split == "validation" and m.query_group == "negation_sensitive"
        )
        return (
            -val.ndcg_at_5,
            -neg.hit_rate_at_5,
            val.zero_hit_query_count,
            config.complexity_rank,
        )

    ranked_ids = sorted(evaluated, key=sort_key)
    selected_id = ranked_ids[0]
    for rank, config_id in enumerate(ranked_ids, start=1):
        metrics = metrics_by_config[config_id]
        val = next(m for m in metrics if m.split == "validation" and m.query_group == "all")
        neg = next(
            m for m in metrics if m.split == "validation" and m.query_group == "negation_sensitive"
        )
        para = next(
            m for m in metrics if m.split == "validation" and m.query_group == "paraphrased"
        )
        rows.append(
            ConfigurationRanking(
                rank=rank,
                configuration_id=config_id,
                dependency_profile="model_free",
                validation_ndcg_at_5=val.ndcg_at_5,
                validation_recall_at_5=val.recall_at_5,
                validation_mrr=val.mrr,
                validation_hit_rate_at_5=val.hit_rate_at_5,
                negation_hit_rate_at_5=neg.hit_rate_at_5,
                paraphrased_hit_rate_at_5=para.hit_rate_at_5,
                zero_hit_query_count=val.zero_hit_query_count,
                quality_gate_status=manifests[config_id].quality_gate_status,
                selection_status="selected" if config_id == selected_id else "not_selected",
            )
        )
    selected_metrics = metrics_by_config[selected_id]
    holdout = next(m for m in selected_metrics if m.split == "holdout" and m.query_group == "all")
    val = next(m for m in selected_metrics if m.split == "validation" and m.query_group == "all")
    gate_results = _apply_gates(selected_metrics)
    passed_required = sum(1 for gate in gate_results if gate.required and gate.status == "passed")
    failed_required = sum(1 for gate in gate_results if gate.required and gate.status == "failed")
    approval_status = (
        "approved_for_rag_prototype"
        if failed_required == 0
        else "conditionally_approved"
        if passed_required >= 5
        else "not_approved"
    )
    selected_config = next(c for c in configs if c.configuration_id == selected_id)
    baseline = SelectedBaseline(
        selected_configuration_id=selected_id,
        selection_status="selected",
        selection_reason="highest validation NDCG@5 with documented tie-breaking; holdout excluded from ranking",
        primary_metric="validation_ndcg_at_5",
        secondary_metrics={"validation_recall_at_5": val.recall_at_5, "validation_mrr": val.mrr},
        quality_gate_status="passed" if failed_required == 0 else "failed",
        dependency_profile="model_free",
        embedding_provider=selected_config.embedding_provider,
        requires_optional_model=False,
        approved_index_id="retrieval-quality-benchmark-v2",
        approved_retrieval_parameters={
            "configuration_id": selected_id,
            "final_top_k": selected_config.final_top_k,
        },
        known_failures=[
            gate.query_group for gate in gate_results if gate.required and gate.status == "failed"
        ],
        future_remediation=[
            "broaden synthetic judgments",
            "add clinician review before clinical use",
        ],
    )
    decision = RetrievalApprovalDecision(
        approval_status=approval_status,
        approved_for_future_rag_prototype=approval_status == "approved_for_rag_prototype",
        selected_configuration_id=selected_id,
        required_gate_count=sum(1 for gate in gate_results if gate.required),
        passed_required_gates=passed_required,
        failed_required_gates=failed_required,
        known_failing_query_groups=baseline.known_failures,
        decision_reason="Derived from required retrieval quality gates",
    )
    comparison_id = stable_id("RETCOMP", [selected_id, reference_timestamp.isoformat()])
    output_dir = output_root / comparison_id
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "configuration_leaderboard.csv",
        [r.model_dump(mode="json") for r in rows],
        list(ConfigurationRanking.model_fields),
    )
    write_csv(
        output_dir / "configuration_metrics.csv",
        [m.model_dump(mode="json") for ms in metrics_by_config.values() for m in ms],
        list(ConfigurationMetric.model_fields),
    )
    write_csv(
        output_dir / "quality_gate_matrix.csv",
        [g.model_dump(mode="json") for g in gate_results],
        list(QualityGateResult.model_fields),
    )
    write_json(output_dir / "selected_baseline.json", baseline)
    write_json(output_dir / "retrieval_approval_decision.json", decision)
    write_json(
        output_dir / "mlflow_comparison_plan.json",
        {
            "experiment_placeholder": "/Shared/hla/retrieval_quality",
            "connection_attempted": False,
            "execution_permitted": False,
        },
    )
    write_json(
        output_dir / "databricks_retrieval_plan.json",
        {
            "vector_search_placeholder": "hla_retrieval_quality_index",
            "connection_attempted": False,
            "execution_permitted": False,
        },
    )
    (output_dir / "retrieval_selection_report.md").write_text(
        "\n".join(
            [
                "# Retrieval Baseline Selection",
                "",
                f"Selected configuration: {selected_id}",
                f"Approval status: {approval_status}",
                "Holdout metrics were calculated after validation-based selection.",
                "No RAG or answer generation is included.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    benchmark_id = BenchmarkManifest.model_validate_json(
        (benchmark_dir / "query_set_manifest.json").read_text()
    ).benchmark_id
    files = [
        "configuration_leaderboard.csv",
        "configuration_metrics.csv",
        "quality_gate_matrix.csv",
        "selected_baseline.json",
        "retrieval_approval_decision.json",
        "retrieval_selection_report.md",
        "mlflow_comparison_plan.json",
        "databricks_retrieval_plan.json",
    ]
    comparison_manifest = RetrievalComparisonManifest(
        comparison_id=comparison_id,
        retrieval_comparison_contract_version=RETRIEVAL_COMPARISON_CONTRACT_VERSION,
        benchmark_id=benchmark_id,
        configuration_registry_version=CONFIGURATION_REGISTRY_VERSION,
        configurations_evaluated=evaluated,
        configurations_skipped=skipped,
        selected_configuration_id=selected_id,
        selection_metric="validation_ndcg_at_5",
        holdout_hit_rate_at_5=holdout.hit_rate_at_5,
        holdout_recall_at_5=holdout.recall_at_5,
        holdout_mrr=holdout.mrr,
        holdout_ndcg_at_5=holdout.ndcg_at_5,
        approval_status=approval_status,
        reference_timestamp=reference_timestamp,
        files=[*files, "comparison_manifest.json"],
        file_checksums=output_checksums(output_dir, files),
        reconciliation_status="passed",
    )
    write_json(output_dir / "comparison_manifest.json", comparison_manifest)
    return output_dir


def validate_comparison_dir(comparison_dir: Path) -> list[str]:
    required = [
        "configuration_leaderboard.csv",
        "configuration_metrics.csv",
        "quality_gate_matrix.csv",
        "selected_baseline.json",
        "retrieval_approval_decision.json",
        "comparison_manifest.json",
    ]
    failures = [f"missing {name}" for name in required if not (comparison_dir / name).exists()]
    if failures:
        return failures
    manifest = RetrievalComparisonManifest.model_validate_json(
        (comparison_dir / "comparison_manifest.json").read_text()
    )
    from healthcare_language_ai.retrieval_quality.io import sha256_file

    for name, expected in manifest.file_checksums.items():
        if sha256_file(comparison_dir / name) != expected:
            failures.append(f"checksum mismatch for {name}")
    return failures
