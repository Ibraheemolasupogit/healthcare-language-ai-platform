"""Reconciliation checks for canonical ingestion outputs."""

from __future__ import annotations

from collections import Counter

from healthcare_language_ai.ingestion.contracts import (
    CanonicalClinicalDocument,
    CanonicalDocumentAnnotation,
    ReconciliationMetric,
    ReconciliationReport,
)


def metric(
    name: str,
    expected: int | str | bool,
    actual: int | str | bool,
    message: str,
    *,
    severity: str = "error",
) -> ReconciliationMetric:
    passed = expected == actual
    return ReconciliationMetric(
        metric_name=name,
        expected_value=expected,
        actual_value=actual,
        status="passed" if passed else "failed",
        severity="info" if passed else severity,
        message=message,
    )


def overall_status(metrics: list[ReconciliationMetric]) -> str:
    if any(item.status == "failed" for item in metrics):
        return "failed"
    if any(item.status == "warning" for item in metrics):
        return "warning"
    return "passed"


def build_reconciliation_report(
    *,
    ingestion_run_id: str,
    source_document_count: int,
    source_annotation_count: int,
    documents: list[CanonicalClinicalDocument],
    annotations: list[CanonicalDocumentAnnotation],
    quarantine_count: int,
    source_document_type_counts: dict[str, int],
    source_annotation_label_counts: dict[str, int],
) -> ReconciliationReport:
    document_ids = [row.document_id for row in documents]
    annotation_ids = [row.annotation_id for row in annotations]
    orphan_count = sum(1 for row in annotations if row.document_id not in set(document_ids))
    duplicate_document_ids = sum(count - 1 for count in Counter(document_ids).values() if count > 1)
    duplicate_annotation_ids = sum(
        count - 1 for count in Counter(annotation_ids).values() if count > 1
    )
    document_type_counts = dict(sorted(Counter(row.document_type for row in documents).items()))
    annotation_label_counts = dict(sorted(Counter(row.label for row in annotations).items()))
    metrics = [
        metric(
            "document_count",
            source_document_count,
            len(documents),
            "canonical document count matches source",
        ),
        metric(
            "annotation_count",
            source_annotation_count,
            len(annotations),
            "canonical annotation count matches source",
        ),
        metric(
            "quarantine_count", 0, quarantine_count, "no records quarantined", severity="warning"
        ),
        metric(
            "duplicate_document_ids", 0, duplicate_document_ids, "document identifiers are unique"
        ),
        metric(
            "duplicate_annotation_ids",
            0,
            duplicate_annotation_ids,
            "annotation identifiers are unique",
        ),
        metric("orphan_annotations", 0, orphan_count, "annotations reference known documents"),
        metric(
            "document_type_counts",
            str(source_document_type_counts),
            str(document_type_counts),
            "document-type counts reconcile",
        ),
        metric(
            "annotation_label_counts",
            str(source_annotation_label_counts),
            str(annotation_label_counts),
            "annotation-label counts reconcile",
        ),
    ]
    return ReconciliationReport(
        reconciliation_schema_version="1.0.0",
        ingestion_run_id=ingestion_run_id,
        overall_status=overall_status(metrics),
        metrics=metrics,
    )
