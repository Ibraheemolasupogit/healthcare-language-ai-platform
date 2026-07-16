"""Preprocessing reconciliation checks."""

from __future__ import annotations

from collections import Counter

from healthcare_language_ai.preprocessing.contracts import (
    PreprocessingReconciliationMetric,
    PreprocessingReconciliationReport,
    ProcessedClinicalDocument,
    ProcessedSection,
    ProcessedSentence,
    ProjectedAnnotation,
)


def metric(
    name: str,
    expected: int | str | bool,
    actual: int | str | bool,
    message: str,
    *,
    warning: bool = False,
) -> PreprocessingReconciliationMetric:
    passed = expected == actual
    return PreprocessingReconciliationMetric(
        metric_name=name,
        expected_value=expected,
        actual_value=actual,
        status="passed" if passed else "warning" if warning else "failed",
        severity="info" if passed else "warning" if warning else "error",
        message=message,
    )


def overall_status(metrics: list[PreprocessingReconciliationMetric]) -> str:
    if any(item.status == "failed" for item in metrics):
        return "failed"
    if any(item.status == "warning" for item in metrics):
        return "warning"
    return "passed"


def build_reconciliation_report(
    *,
    run_id: str,
    source_document_count: int,
    source_annotation_count: int,
    documents: list[ProcessedClinicalDocument],
    sections: list[ProcessedSection],
    sentences: list[ProcessedSentence],
    projections: list[ProjectedAnnotation],
    output_checksum_status: bool,
    databricks_plan_valid: bool,
) -> PreprocessingReconciliationReport:
    document_ids = [item.document_id for item in documents]
    section_ids = [item.section_id for item in sections]
    sentence_ids = [item.sentence_id for item in sentences]
    invalid_sentence_offsets = sum(
        1
        for item in sentences
        if item.sentence_text
        != next(doc.normalised_text for doc in documents if doc.document_id == item.document_id)[
            item.start_offset : item.end_offset
        ]
    )
    metrics = [
        metric(
            "document_count",
            source_document_count,
            len(documents),
            "processed document count matches source",
        ),
        metric(
            "annotation_projection_count",
            source_annotation_count,
            len(projections),
            "annotation projection count matches source",
        ),
        metric(
            "duplicate_document_ids",
            0,
            len(document_ids) - len(set(document_ids)),
            "document IDs are unique",
        ),
        metric(
            "duplicate_section_ids",
            0,
            len(section_ids) - len(set(section_ids)),
            "section IDs are unique",
        ),
        metric(
            "duplicate_sentence_ids",
            0,
            len(sentence_ids) - len(set(sentence_ids)),
            "sentence IDs are unique",
        ),
        metric(
            "invalid_sentence_offsets",
            0,
            invalid_sentence_offsets,
            "sentence offsets match normalised text",
        ),
        metric("manifest_checksums", True, output_checksum_status, "manifest checksums validate"),
        metric(
            "databricks_plan_consistency",
            True,
            databricks_plan_valid,
            "Databricks plan is consistent",
        ),
        metric(
            "section_count_positive", True, len(sections) > 0, "sections were parsed", warning=True
        ),
    ]
    return PreprocessingReconciliationReport(
        reconciliation_schema_version="1.0.0",
        preprocessing_run_id=run_id,
        overall_status=overall_status(metrics),
        metrics=metrics,
    )


def count_by(items: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(items).items()))
