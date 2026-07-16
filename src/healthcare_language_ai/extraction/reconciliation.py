"""Reconciliation checks for extraction evidence."""

from __future__ import annotations

from collections import Counter

from healthcare_language_ai.extraction.contracts import (
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_ENTITY_LABELS,
    DocumentClassificationPrediction,
    EntityPrediction,
    PredictionReconciliationMetric,
    PredictionReconciliationReport,
    RuleMatch,
    SuppressedCandidate,
)
from healthcare_language_ai.preprocessing.contracts import ProcessedClinicalDocument


def count_by(items: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(items).items()))


def metric(
    name: str,
    expected: int | str | bool,
    actual: int | str | bool,
    message: str,
    *,
    warning: bool = False,
) -> PredictionReconciliationMetric:
    passed = expected == actual
    return PredictionReconciliationMetric(
        metric_name=name,
        expected_value=expected,
        actual_value=actual,
        status="passed" if passed else "warning" if warning else "failed",
        severity="info" if passed else "warning" if warning else "error",
        message=message,
    )


def overall_status(metrics: list[PredictionReconciliationMetric]) -> str:
    if any(item.status == "failed" for item in metrics):
        return "failed"
    if any(item.status == "warning" for item in metrics):
        return "warning"
    return "passed"


def build_reconciliation_report(
    *,
    extraction_run_id: str,
    documents: list[ProcessedClinicalDocument],
    candidates: list[RuleMatch],
    predictions: list[EntityPrediction],
    classifications: list[DocumentClassificationPrediction],
    suppressed: list[SuppressedCandidate],
    duplicate_prediction_count: int,
    output_checksum_status: bool,
) -> PredictionReconciliationReport:
    text_by_doc = {item.document_id: item.normalised_text for item in documents}
    prediction_ids = [item.prediction_id for item in predictions]
    invalid_offsets = sum(
        1
        for item in predictions
        if item.start_offset is None
        or item.end_offset is None
        or item.start_offset >= item.end_offset
        or text_by_doc[item.document_id][item.start_offset : item.end_offset] != item.matched_text
    )
    unsupported_labels = sum(1 for item in predictions if item.label not in SUPPORTED_ENTITY_LABELS)
    unsupported_classes = sum(
        1
        for item in classifications
        if item.predicted_document_type not in SUPPORTED_DOCUMENT_TYPES
    )
    metrics = [
        metric(
            "document_classification_count",
            len(documents),
            len(classifications),
            "one document classification exists for each source document",
        ),
        metric(
            "candidate_accounting",
            len(candidates),
            len(predictions) + len(suppressed) + duplicate_prediction_count,
            "accepted, suppressed and duplicate candidates reconcile",
        ),
        metric(
            "duplicate_prediction_ids",
            0,
            len(prediction_ids) - len(set(prediction_ids)),
            "prediction IDs are unique",
        ),
        metric("invalid_prediction_offsets", 0, invalid_offsets, "prediction offsets are valid"),
        metric("unsupported_entity_labels", 0, unsupported_labels, "entity labels are supported"),
        metric(
            "unsupported_document_classes",
            0,
            unsupported_classes,
            "document classes are supported",
        ),
        metric(
            "confidence_bounds",
            True,
            all(0 <= item.confidence <= 1 for item in predictions),
            "confidence values are bounded",
        ),
        metric("manifest_checksums", True, output_checksum_status, "manifest checksums validate"),
    ]
    return PredictionReconciliationReport(
        reconciliation_schema_version="1.0.0",
        extraction_run_id=extraction_run_id,
        overall_status=overall_status(metrics),
        metrics=metrics,
    )
