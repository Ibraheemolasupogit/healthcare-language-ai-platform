"""Human-review-ready relevance pack generation."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.retrieval_quality.contracts import (
    BenchmarkManifest,
    ReviewerPackManifest,
)
from healthcare_language_ai.retrieval_quality.io import (
    output_checksums,
    read_jsonl,
    stable_id,
    write_csv,
    write_json,
)


def write_review_pack(*, benchmark_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = BenchmarkManifest.model_validate_json(
        (benchmark_dir / "query_set_manifest.json").read_text()
    )
    queries = read_jsonl(benchmark_dir / "retrieval_queries_v2.jsonl")
    judgments = read_jsonl(benchmark_dir / "relevance_judgments_v2.jsonl")
    write_csv(
        output_dir / "query-review.csv",
        [
            {
                "query_id": row["query_id"],
                "query_text": row["query_text"],
                "query_category": row["query_category"],
                "split": row["split"],
                "review_question": "Is the query clear for the synthetic benchmark?",
            }
            for row in queries
        ],
        ["query_id", "query_text", "query_category", "split", "review_question"],
    )
    write_csv(
        output_dir / "relevance-review.csv",
        [
            {
                "judgment_id": row["judgment_id"],
                "query_id": row["query_id"],
                "retrieval_unit_id": row["retrieval_unit_id"],
                "relevance_grade": row["relevance_grade"],
                "reviewer_role": row["reviewer_role"],
                "review_prompt": "Confirm relevance grade or record disagreement.",
            }
            for row in judgments
        ],
        [
            "judgment_id",
            "query_id",
            "retrieval_unit_id",
            "relevance_grade",
            "reviewer_role",
            "review_prompt",
        ],
    )
    write_csv(
        output_dir / "ambiguous-judgments.csv",
        [],
        ["query_id", "retrieval_unit_id", "ambiguity_reason", "reviewer_notes"],
    )
    write_csv(
        output_dir / "disagreement-template.csv",
        [],
        ["judgment_id", "reviewer_role", "proposed_grade", "reason", "reviewed_at"],
    )
    (output_dir / "review-guidance.md").write_text(
        "\n".join(
            [
                "# Retrieval Review Guidance",
                "",
                "This pack supports future review of synthetic benchmark judgments.",
                "It does not claim clinician validation.",
                "Reviewers should assess query clarity, relevance grade, missing relevant units, distractor validity, metadata filters, negation, and numeric matching.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    files = [
        "query-review.csv",
        "relevance-review.csv",
        "ambiguous-judgments.csv",
        "disagreement-template.csv",
        "review-guidance.md",
    ]
    pack_manifest = ReviewerPackManifest(
        reviewer_pack_id=stable_id("RPACK", [manifest.benchmark_id, manifest.query_count]),
        benchmark_id=manifest.benchmark_id,
        query_count=manifest.query_count,
        relevance_judgment_count=manifest.relevance_judgment_count,
        files=[*files, "review-manifest.json"],
        file_checksums=output_checksums(output_dir, files),
        reviewer_roles=[
            "synthetic_benchmark_author",
            "automated_lineage_check",
            "portfolio_reviewer_placeholder",
        ],
        clinician_validation_claimed=False,
    )
    write_json(output_dir / "review-manifest.json", pack_manifest)
    return output_dir
