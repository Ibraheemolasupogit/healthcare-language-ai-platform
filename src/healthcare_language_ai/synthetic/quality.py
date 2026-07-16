"""Structured data-quality reporting."""

from __future__ import annotations

from healthcare_language_ai.synthetic.manifest import annotation_label_counts, document_type_counts
from healthcare_language_ai.synthetic.models import (
    DataQualityReport,
    SyntheticDocumentRecord,
    ValidationCheck,
)


def build_quality_report(
    records: list[SyntheticDocumentRecord], checks: list[ValidationCheck]
) -> DataQualityReport:
    failed = any(check.status == "failed" for check in checks)
    warned = any(check.status == "warning" for check in checks)
    status = "failed" if failed else "warning" if warned else "passed"
    return DataQualityReport(
        dataset_name="synthetic_clinical_documents",
        schema_version="1.0.0",
        validation_status=status,
        checks=checks,
        record_count=len(records),
        document_type_counts=document_type_counts(records),
        annotation_label_counts=annotation_label_counts(records),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
    )
