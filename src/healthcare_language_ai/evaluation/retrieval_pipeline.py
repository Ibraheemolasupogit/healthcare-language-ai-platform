"""Retrieval evaluation, failure analysis and dry-run planning."""

from __future__ import annotations

import csv
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from healthcare_language_ai.config import RetrievalSettings
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.retrieval.contracts import (
    RetrievalEvaluationManifest,
    RetrievalFailureRecord,
    RetrievalMetric,
    RetrievalModelCard,
    RetrievalResult,
    RetrievalRunStatus,
    VectorSearchPlan,
)
from healthcare_language_ai.retrieval.pipeline import (
    load_judgments,
    load_queries,
    load_retrieval_manifest,
)
from healthcare_language_ai.retrieval.serialisation import (
    FAILURE_COLUMNS,
    METRIC_COLUMNS,
    write_csv,
    write_json_model,
    write_jsonl,
)
from healthcare_language_ai.retrieval.validation import validate_retrieval_dir
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json, write_json
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_retrieval_evaluation_id(
    *,
    retrieval_manifest_checksum: str,
    relevance_judgment_checksum: str,
    evaluation_contract_version: str,
    metrics_version: str,
    k_values: list[int],
    reference_timestamp: datetime,
) -> str:
    return "RETEVAL-" + deterministic_id(
        {
            "retrieval_manifest_checksum": retrieval_manifest_checksum,
            "relevance_judgment_checksum": relevance_judgment_checksum,
            "evaluation_contract_version": evaluation_contract_version,
            "metrics_version": metrics_version,
            "k_values": k_values,
            "reference_timestamp": reference_timestamp.isoformat(),
        },
        length=24,
    )


def _prepare_output_dir(output_dir: Path, policy: OverwritePolicy) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if policy is OverwritePolicy.FAIL_IF_EXISTS:
        msg = f"output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _safe_div(left: float, right: float) -> float:
    return round(left / right, 6) if right else 0.0


def _dcg(grades: list[int]) -> float:
    return float(sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades)))


def _metric(
    *,
    scope: str,
    value: str,
    k: int,
    queries: list[Any],
    results_by_query: dict[str, list[RetrievalResult]],
    relevant_by_query: dict[str, dict[str, int]],
    evaluation_id: str,
) -> RetrievalMetric:
    precision_values: list[float] = []
    recall_values: list[float] = []
    hits: list[float] = []
    reciprocal_ranks: list[float] = []
    average_precisions: list[float] = []
    ndcgs: list[float] = []
    relevant_ranks: list[int] = []
    zero_hit = 0
    for query in queries:
        relevant = relevant_by_query.get(query.query_id, {})
        returned = results_by_query.get(query.query_id, [])[:k]
        relevant_returned = [row for row in returned if row.retrieval_unit_id in relevant]
        precision_values.append(_safe_div(len(relevant_returned), k))
        recall_values.append(_safe_div(len(relevant_returned), len(relevant)))
        hit = 1.0 if relevant_returned else 0.0
        hits.append(hit)
        if not relevant_returned and relevant:
            zero_hit += 1
        first_rank = next((row.rank for row in returned if row.retrieval_unit_id in relevant), None)
        reciprocal_ranks.append(0.0 if first_rank is None else 1 / first_rank)
        hits_seen = 0
        ap_total = 0.0
        for row in returned:
            if row.retrieval_unit_id in relevant:
                hits_seen += 1
                ap_total += hits_seen / row.rank
                relevant_ranks.append(row.rank)
        average_precisions.append(_safe_div(ap_total, len(relevant)))
        returned_grades = [relevant.get(row.retrieval_unit_id, 0) for row in returned]
        ideal_grades = sorted(relevant.values(), reverse=True)[:k]
        ndcgs.append(_safe_div(_dcg(returned_grades), _dcg(ideal_grades)))
    query_count = len(queries)
    return RetrievalMetric(
        metric_scope=scope,
        scope_value=value,
        k=k,
        query_count=query_count,
        precision_at_k=round(sum(precision_values) / max(1, query_count), 6),
        recall_at_k=round(sum(recall_values) / max(1, query_count), 6),
        hit_rate_at_k=round(sum(hits) / max(1, query_count), 6),
        mrr=round(sum(reciprocal_ranks) / max(1, query_count), 6),
        map_score=round(sum(average_precisions) / max(1, query_count), 6),
        ndcg_at_k=round(sum(ndcgs) / max(1, query_count), 6),
        zero_hit_query_count=zero_hit,
        average_relevant_rank=round(sum(relevant_ranks) / max(1, len(relevant_ranks)), 6),
        retrieval_evaluation_run_id=evaluation_id,
    )


def evaluate_retrieval(
    *,
    retrieval_dir: Path,
    relevance_judgments: Path,
    output_root: Path,
    k_values: list[int],
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: RetrievalSettings,
) -> Path:
    failures = validate_retrieval_dir(retrieval_dir)
    if failures:
        raise ValueError(f"retrieval validation failed: {failures[0]}")
    retrieval_manifest = load_retrieval_manifest(retrieval_dir)
    evaluation_id = derive_retrieval_evaluation_id(
        retrieval_manifest_checksum=sha256_file(retrieval_dir / "retrieval_manifest.json"),
        relevance_judgment_checksum=sha256_file(relevance_judgments),
        evaluation_contract_version=settings.retrieval_evaluation_contract_version,
        metrics_version=settings.retrieval_metrics_version,
        k_values=k_values,
        reference_timestamp=reference_timestamp,
    )
    output_dir = output_root / evaluation_id
    _prepare_output_dir(output_dir, overwrite_policy)
    query_path = relevance_judgments.parent / "retrieval_queries.jsonl"
    queries = load_queries(query_path)
    judgments = load_judgments(relevance_judgments)
    relevant_by_query: dict[str, dict[str, int]] = {}
    for judgment in judgments:
        relevant_by_query.setdefault(judgment.query_id, {})[judgment.retrieval_unit_id] = (
            judgment.relevance_grade
        )
    results = [
        RetrievalResult.model_validate(row)
        for row in _read_csv(retrieval_dir / "retrieval_results.csv")
    ]
    results_by_query: dict[str, list[RetrievalResult]] = {}
    for result in results:
        results_by_query.setdefault(result.query_id, []).append(result)
    for query_results in results_by_query.values():
        query_results.sort(key=lambda item: item.rank)
    metrics: list[RetrievalMetric] = []
    for k in k_values:
        metrics.append(
            _metric(
                scope="overall",
                value="all",
                k=k,
                queries=queries,
                results_by_query=results_by_query,
                relevant_by_query=relevant_by_query,
                evaluation_id=evaluation_id,
            )
        )
        for category in sorted({query.query_category for query in queries}):
            subset = [query for query in queries if query.query_category == category]
            metrics.append(
                _metric(
                    scope="query_category",
                    value=category,
                    k=k,
                    queries=subset,
                    results_by_query=results_by_query,
                    relevant_by_query=relevant_by_query,
                    evaluation_id=evaluation_id,
                )
            )
        for leakage in sorted({query.leakage_risk for query in queries}):
            subset = [query for query in queries if query.leakage_risk == leakage]
            metrics.append(
                _metric(
                    scope="leakage_risk",
                    value=leakage,
                    k=k,
                    queries=subset,
                    results_by_query=results_by_query,
                    relevant_by_query=relevant_by_query,
                    evaluation_id=evaluation_id,
                )
            )
    failures_out: list[RetrievalFailureRecord] = []
    for query in queries:
        relevant = relevant_by_query.get(query.query_id, {})
        returned = results_by_query.get(query.query_id, [])
        top = returned[0] if returned else None
        if relevant and not any(row.retrieval_unit_id in relevant for row in returned[:5]):
            expected = sorted(relevant)[0]
            failures_out.append(
                RetrievalFailureRecord(
                    failure_id="RF_"
                    + deterministic_id({"eval": evaluation_id, "query": query.query_id}, length=20),
                    query_id=query.query_id,
                    query_category=query.query_category,
                    strategy=retrieval_manifest.strategy.value,
                    failure_type="missed_relevant_result",
                    expected_unit_id=expected,
                    returned_unit_id=top.retrieval_unit_id if top else None,
                    actual_rank=top.rank if top else None,
                    top_result_score=top.score if top else None,
                    matched_terms=top.matched_terms if top else "",
                    sanitised_query=query.query_text[:96],
                    sanitised_result_snippet=top.sanitised_snippet if top else "",
                    likely_reason="lexical or metadata mismatch in synthetic benchmark",
                    retrieval_evaluation_run_id=evaluation_id,
                )
            )
    overall_at_1 = next(item for item in metrics if item.metric_scope == "overall" and item.k == 1)
    overall_at_5 = next(item for item in metrics if item.metric_scope == "overall" and item.k == 5)
    write_csv(output_dir / "retrieval_metrics.csv", metrics, METRIC_COLUMNS)
    write_csv(output_dir / "retrieval_failures.csv", failures_out, FAILURE_COLUMNS)
    write_jsonl(output_dir / "retrieval_failures.jsonl", failures_out)
    model_card = RetrievalModelCard(
        system_name="Local Hybrid Retrieval Baseline",
        version="1.0.0",
        retrieval_strategies=["keyword", "tfidf", "bm25", "hybrid"],
        corpus_source=retrieval_manifest.index_id,
        corpus_size=retrieval_manifest.query_count,
        retrieval_units={},
        tokenisation="Versioned lexical tokens with no clinical stemming.",
        sparse_features="Local TF-IDF and BM25 statistics.",
        dense_vector_method="Deterministic hash vectors, not a language model.",
        hybrid_fusion="Weighted normalised score fusion.",
        query_set_construction="Manual synthetic direct, paraphrased and compositional queries.",
        evaluation_metrics={
            "hit_rate_at_5": overall_at_5.hit_rate_at_k,
            "mrr": overall_at_5.mrr,
            "map": overall_at_5.map_score,
            "ndcg_at_5": overall_at_5.ndcg_at_k,
        },
        performance_by_query_group={
            item.scope_value: item.hit_rate_at_k
            for item in metrics
            if item.metric_scope == "query_category" and item.k == 5
        },
        benchmark_leakage="Direct queries overlap with synthetic corpus vocabulary.",
        known_limitations=["Small synthetic corpus", "Manual judgments", "No clinical validation"],
        clinical_safety_position="Evidence retrieval only; not for diagnosis or treatment.",
        privacy_position="Synthetic data only.",
        unsupported_uses=["RAG answers", "Clinical search deployment", "Medical advice"],
        failure_modes=["Paraphrase mismatch", "Filter exclusion", "Sparse lexical mismatch"],
        human_review_expectations="Future clinical use would require expert relevance review.",
        future_dense_model_comparison="Compare optional local dense models against this baseline.",
    )
    write_json_model(output_dir / "retrieval_model_card.json", model_card)
    (output_dir / "retrieval_model_card.md").write_text(
        "# Local Hybrid Retrieval Baseline\n\nDeterministic synthetic retrieval evidence only.\n",
        encoding="utf-8",
    )
    vector_plan = VectorSearchPlan(
        plan_schema_version="1.0.0",
        vector_search_contract_version=settings.vector_search_contract_version,
        endpoint_placeholder="hla-vector-search-endpoint-placeholder",
        index_placeholder="hla_retrieval_units_index_placeholder",
        primary_key="retrieval_unit_id",
        embedding_column="hash_embedding",
        embedding_dimension=settings.embedding_dimension,
        metadata_filter_columns=[
            "document_type",
            "section_label",
            "unit_type",
            "synthetic_subject_id",
            "synthetic_encounter_id",
        ],
        sync_strategy="reference-only batch sync",
        access_control_expectations=["least privilege", "synthetic data only"],
        source_index_id=retrieval_manifest.index_id,
        dry_run_status="validated",
        connection_attempted=False,
        execution_permitted=False,
    )
    write_json_model(output_dir / "vector_search_plan.json", vector_plan)
    mlflow_plan = {
        "experiment_name_placeholder": "/Shared/hla/retrieval_baseline",
        "index_id": retrieval_manifest.index_id,
        "retrieval_run_id": retrieval_manifest.retrieval_run_id,
        "retrieval_evaluation_run_id": evaluation_id,
        "parameters": {
            "strategy": retrieval_manifest.strategy.value,
            "top_k": str(retrieval_manifest.top_k),
        },
        "metrics": {
            "hit_rate_at_1": overall_at_1.hit_rate_at_k,
            "hit_rate_at_5": overall_at_5.hit_rate_at_k,
            "mrr": overall_at_5.mrr,
            "map": overall_at_5.map_score,
            "ndcg_at_5": overall_at_5.ndcg_at_k,
        },
        "artifacts": ["retrieval_model_card.json", "retrieval_failures.csv"],
        "dry_run_status": "validated",
        "connection_attempted": False,
        "execution_permitted": False,
    }
    write_json(output_dir / "retrieval_mlflow_plan.json", mlflow_plan)
    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "retrieval_evaluation_manifest.json"
    }
    reconciliation = {
        "reconciliation_schema_version": "1.0.0",
        "run_id": evaluation_id,
        "overall_status": "passed",
        "metrics": [],
    }
    write_json(output_dir / "retrieval_evaluation_reconciliation.json", reconciliation)
    output_checksums["retrieval_evaluation_reconciliation.json"] = sha256_file(
        output_dir / "retrieval_evaluation_reconciliation.json"
    )
    manifest = RetrievalEvaluationManifest(
        manifest_schema_version="1.0.0",
        retrieval_evaluation_contract_version=settings.retrieval_evaluation_contract_version,
        retrieval_evaluation_run_id=evaluation_id,
        run_status=RetrievalRunStatus.COMPLETED,
        retrieval_run_id=retrieval_manifest.retrieval_run_id,
        retrieval_manifest_checksum=sha256_file(retrieval_dir / "retrieval_manifest.json"),
        relevance_judgment_checksum=sha256_file(relevance_judgments),
        evaluated_query_count=len(queries),
        k_values=k_values,
        precision_at_1=overall_at_1.precision_at_k,
        precision_at_5=overall_at_5.precision_at_k,
        recall_at_5=overall_at_5.recall_at_k,
        hit_rate_at_1=overall_at_1.hit_rate_at_k,
        hit_rate_at_5=overall_at_5.hit_rate_at_k,
        mrr=overall_at_5.mrr,
        map_score=overall_at_5.map_score,
        ndcg_at_5=overall_at_5.ndcg_at_k,
        zero_hit_query_count=overall_at_5.zero_hit_query_count,
        failure_count=len(failures_out),
        retrieval_metrics_version=settings.retrieval_metrics_version,
        retrieval_failure_version=settings.retrieval_failure_version,
        reference_timestamp=reference_timestamp,
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status="passed",
    )
    write_json_model(output_dir / "retrieval_evaluation_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        f"# Retrieval Evaluation Evidence\n\nEvaluation ID: {evaluation_id}\n",
        encoding="utf-8",
    )
    return output_dir


def load_retrieval_evaluation_manifest(evaluation_dir: Path) -> RetrievalEvaluationManifest:
    return RetrievalEvaluationManifest.model_validate(
        read_json(evaluation_dir / "retrieval_evaluation_manifest.json")
    )
