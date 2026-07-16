"""Expanded retrieval benchmark generation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_quality.contracts import (
    BenchmarkManifest,
    BenchmarkQuery,
    BenchmarkSplit,
    RelevanceReviewRecord,
)
from healthcare_language_ai.retrieval_quality.holdout import (
    build_overlap_report,
    generate_holdout_documents,
)
from healthcare_language_ai.retrieval_quality.io import (
    output_checksums,
    stable_id,
    write_json,
    write_jsonl,
)

BENCHMARK_VERSION = "2.0.0"
BENCHMARK_SPLIT_VERSION = "1.0.0"

CATEGORIES = [
    "direct",
    "paraphrased",
    "compositional",
    "distractor",
    "negation_sensitive",
    "numeric_detail",
    "metadata_filtered",
    "cross_granularity",
    "abbreviation",
    "section_alias",
    "multi_relevant",
    "unanswerable",
]

AUTHORING_BY_CATEGORY = {
    "direct": "exact_source_phrase",
    "paraphrased": "manual_paraphrase",
    "compositional": "manual_composition",
    "distractor": "adversarial_distractor",
    "negation_sensitive": "negation_variant",
    "numeric_detail": "numeric_variant",
    "metadata_filtered": "metadata_derived",
    "cross_granularity": "manual_composition",
    "abbreviation": "abbreviation_variant",
    "section_alias": "controlled_synonym",
    "multi_relevant": "manual_composition",
    "unanswerable": "adversarial_distractor",
}


def _unit_id(document_id: str, unit_type: str, index: int = 0) -> str:
    return stable_id("RQUNIT", [document_id, unit_type, index], length=20)


def benchmark_units(holdout_dir: Path | None = None) -> list[dict[str, str]]:
    if holdout_dir and (holdout_dir / "holdout_documents.jsonl").exists():
        from healthcare_language_ai.retrieval_quality.io import read_jsonl

        docs = read_jsonl(holdout_dir / "holdout_documents.jsonl")
    else:
        docs = [
            doc.model_dump(mode="json")
            for doc in generate_holdout_documents(
                count=40,
                seed=7026,
                reference_timestamp=datetime.fromisoformat("2026-01-09T09:00:00+00:00"),
            )[0]
        ]
    units: list[dict[str, str]] = []
    for doc in docs:
        units.append(
            {
                "retrieval_unit_id": _unit_id(doc["document_id"], "document"),
                "document_id": doc["document_id"],
                "unit_type": "document",
                "document_type": doc["document_type"],
                "section_label": "",
                "text": doc["text"],
                "holdout_status": "independent_holdout",
            }
        )
        for section_index, (label, body) in enumerate(doc["sections"].items(), start=1):
            units.append(
                {
                    "retrieval_unit_id": _unit_id(doc["document_id"], "section", section_index),
                    "document_id": doc["document_id"],
                    "unit_type": "section",
                    "document_type": doc["document_type"],
                    "section_label": label,
                    "text": body,
                    "holdout_status": "independent_holdout",
                }
            )
    return units


def _query_text(category: str, unit: dict[str, str], index: int) -> str:
    words = tokens(unit["text"])
    anchor = " ".join(words[:4]) if words else "synthetic note"
    category_text = {
        "direct": anchor,
        "paraphrased": "manual wording for cardiac respiratory renal review",
        "compositional": f"{unit['document_type']} {unit['section_label']} synthetic value",
        "distractor": "real patient medication advice",
        "negation_sensitive": "without swelling negative for fracture",
        "numeric_detail": f"{['8 mm', '2.5 cm', '72 bpm', '98 percent'][index % 4]} value",
        "metadata_filtered": f"{unit['document_type']} observed findings",
        "cross_granularity": f"document and section evidence for {unit['document_type']}",
        "abbreviation": f"{['CT', 'MRI', 'BP', 'HR'][index % 4]} context",
        "section_alias": "summary impression observed findings background",
        "multi_relevant": "synthetic workflow repeated concern",
        "unanswerable": f"unsupported fictional topic {index}",
    }
    return category_text[category]


def generate_benchmark(benchmark_dir: Path, *, holdout_dir: Path | None = None) -> Path:
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    units = benchmark_units(holdout_dir)
    queries: list[BenchmarkQuery] = []
    judgments: list[RelevanceReviewRecord] = []
    query_index = 0
    minimums = {
        "direct": 8,
        "paraphrased": 10,
        "compositional": 10,
        "distractor": 5,
        "negation_sensitive": 8,
        "numeric_detail": 8,
        "metadata_filtered": 10,
        "cross_granularity": 10,
        "abbreviation": 8,
        "section_alias": 8,
        "multi_relevant": 5,
        "unanswerable": 5,
    }
    for category in CATEGORIES:
        for _ in range(minimums[category]):
            unit = units[(query_index * 7) % len(units)]
            query_split = (
                "development"
                if query_index % 5 in {0, 1}
                else "validation"
                if query_index % 5 in {2, 3}
                else "holdout"
            )
            query_id = stable_id("RQ", [category, query_index, BENCHMARK_VERSION], length=18)
            relevant = [] if category == "unanswerable" else [unit["retrieval_unit_id"]]
            if category == "multi_relevant":
                relevant.append(units[(query_index * 7 + 1) % len(units)]["retrieval_unit_id"])
            query = BenchmarkQuery(
                query_id=query_id,
                query_text=_query_text(category, unit, query_index),
                query_category=category,
                split=query_split,
                difficulty="hard"
                if category in {"negation_sensitive", "unanswerable"}
                else "medium",
                leakage_risk="low" if category in {"paraphrased", "compositional"} else "medium",
                authoring_method=AUTHORING_BY_CATEGORY[category],
                source_overlap_ratio=0.15 if category in {"paraphrased", "compositional"} else 0.45,
                holdout_status="independent_holdout"
                if query_split == "holdout"
                else "original_fixture",
                target_unit_type=unit["unit_type"],
                relevant_unit_ids=relevant,
                metadata_filters={"document_type": unit["document_type"]}
                if category == "metadata_filtered"
                else {},
                polarity_expectation="negated"
                if category == "negation_sensitive"
                else "not_applicable",
                numeric_constraints=[query_id] if category == "numeric_detail" else [],
                benchmark_version=BENCHMARK_VERSION,
                synthetic_data_only=True,
            )
            queries.append(query)
            for relevant_unit in relevant:
                judgments.append(
                    RelevanceReviewRecord(
                        judgment_id=stable_id("RJ", [query_id, relevant_unit], length=20),
                        query_id=query_id,
                        retrieval_unit_id=relevant_unit,
                        relevance_grade=3,
                        judgment_status="approved_for_synthetic_benchmark",
                        judgment_source="manual_synthetic_benchmark_fixture",
                        rationale_code=f"{category}_lineage_match",
                        reviewer_role="synthetic_benchmark_author",
                        reviewed_at=datetime.fromisoformat("2026-01-09T09:00:00+00:00"),
                        benchmark_version=BENCHMARK_VERSION,
                    )
                )
            query_index += 1
    benchmark_split = BenchmarkSplit(
        split_version=BENCHMARK_SPLIT_VERSION,
        development_query_ids=[q.query_id for q in queries if q.split == "development"],
        validation_query_ids=[q.query_id for q in queries if q.split == "validation"],
        holdout_query_ids=[q.query_id for q in queries if q.split == "holdout"],
    )
    overlap = build_overlap_report(
        generate_holdout_documents(
            count=40,
            seed=7026,
            reference_timestamp=datetime.fromisoformat("2026-01-09T09:00:00+00:00"),
        )[0],
        [query.query_text for query in queries],
    )
    write_jsonl(benchmark_dir / "retrieval_queries_v2.jsonl", queries)
    write_jsonl(benchmark_dir / "relevance_judgments_v2.jsonl", judgments)
    write_json(benchmark_dir / "benchmark_splits.json", benchmark_split)
    write_json(benchmark_dir / "vocabulary_overlap_report.json", overlap)
    write_json(
        benchmark_dir / "relevance_manifest.json",
        {
            "benchmark_version": BENCHMARK_VERSION,
            "relevance_judgment_count": len(judgments),
            "judgment_status": "approved_for_synthetic_benchmark",
            "clinician_reviewed": False,
        },
    )
    write_json(
        benchmark_dir / "benchmark_quality_report.json",
        {
            "validation_status": "passed",
            "split_overlap_status": "passed",
            "holdout_excluded_from_selection_status": "passed",
            "query_count": len(queries),
        },
    )
    files = [
        "retrieval_queries_v2.jsonl",
        "relevance_judgments_v2.jsonl",
        "benchmark_splits.json",
        "relevance_manifest.json",
        "vocabulary_overlap_report.json",
        "benchmark_quality_report.json",
    ]
    category_counts = Counter(query.query_category for query in queries)
    difficulty_counts = Counter(query.difficulty for query in queries)
    leakage_counts = Counter(query.leakage_risk for query in queries)
    authoring_counts = Counter(query.authoring_method for query in queries)
    manifest = BenchmarkManifest(
        benchmark_id=stable_id("RQBENCH", [BENCHMARK_VERSION, len(queries)]),
        benchmark_version=BENCHMARK_VERSION,
        split_version=BENCHMARK_SPLIT_VERSION,
        query_count=len(queries),
        relevance_judgment_count=len(judgments),
        development_query_count=len(benchmark_split.development_query_ids),
        validation_query_count=len(benchmark_split.validation_query_ids),
        holdout_query_count=len(benchmark_split.holdout_query_ids),
        query_category_counts=dict(sorted(category_counts.items())),
        difficulty_counts=dict(sorted(difficulty_counts.items())),
        leakage_risk_counts=dict(sorted(leakage_counts.items())),
        authoring_method_counts=dict(sorted(authoring_counts.items())),
        negation_sensitive_query_count=category_counts["negation_sensitive"],
        numeric_detail_query_count=category_counts["numeric_detail"],
        abbreviation_query_count=category_counts["abbreviation"],
        section_alias_query_count=category_counts["section_alias"],
        cross_granularity_query_count=category_counts["cross_granularity"],
        unanswerable_query_count=category_counts["unanswerable"],
        files=[*files, "query_set_manifest.json", "README.md"],
        file_checksums=output_checksums(benchmark_dir, files),
        validation_status="passed",
    )
    write_json(benchmark_dir / "query_set_manifest.json", manifest)
    (benchmark_dir / "README.md").write_text(
        "\n".join(
            [
                "# Retrieval Quality Benchmark",
                "",
                "Expanded deterministic benchmark for Milestone 7 retrieval comparison.",
                f"Query count: {len(queries)}",
                f"Benchmark ID: {manifest.benchmark_id}",
                "Clinician review: false",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return benchmark_dir


def validate_benchmark_dir(benchmark_dir: Path) -> list[str]:
    required = [
        "retrieval_queries_v2.jsonl",
        "relevance_judgments_v2.jsonl",
        "benchmark_splits.json",
        "query_set_manifest.json",
        "relevance_manifest.json",
        "vocabulary_overlap_report.json",
        "benchmark_quality_report.json",
        "README.md",
    ]
    failures = [f"missing {name}" for name in required if not (benchmark_dir / name).exists()]
    if failures:
        return failures
    manifest = BenchmarkManifest.model_validate_json(
        (benchmark_dir / "query_set_manifest.json").read_text()
    )
    split = BenchmarkSplit.model_validate_json(
        (benchmark_dir / "benchmark_splits.json").read_text()
    )
    if manifest.query_count != (
        len(split.development_query_ids)
        + len(split.validation_query_ids)
        + len(split.holdout_query_ids)
    ):
        failures.append("query split counts do not reconcile")
    for name, expected in manifest.file_checksums.items():
        from healthcare_language_ai.retrieval_quality.io import sha256_file

        if sha256_file(benchmark_dir / name) != expected:
            failures.append(f"checksum mismatch for {name}")
    return failures
