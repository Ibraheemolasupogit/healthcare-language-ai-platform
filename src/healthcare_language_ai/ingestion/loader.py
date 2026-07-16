"""Load and validate source synthetic datasets."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.synthetic.models import (
    DataQualityReport,
    DatasetManifest,
    DocumentAnnotation,
    SyntheticClinicalDocument,
)
from healthcare_language_ai.synthetic.serialization import read_json, read_jsonl
from healthcare_language_ai.synthetic.validation import validate_dataset_dir, validation_status


def validate_source_dataset(source_dir: Path, *, max_document_text_length: int) -> DatasetManifest:
    """Run mandatory source validation before ingestion."""
    checks = validate_dataset_dir(source_dir, max_document_text_length=max_document_text_length)
    if validation_status(checks) != "passed":
        msg = "source dataset failed mandatory validation"
        raise DataGovernanceError(msg)
    manifest = DatasetManifest.model_validate(read_json(source_dir / "dataset_manifest.json"))
    quality = DataQualityReport.model_validate(read_json(source_dir / "data_quality_report.json"))
    if not manifest.synthetic_data_only or not manifest.clinical_use_prohibited:
        msg = "source manifest governance flags are not safe"
        raise DataGovernanceError(msg)
    if quality.validation_status != "passed":
        msg = "source quality report status is not passed"
        raise DataGovernanceError(msg)
    return manifest


def load_source_documents(source_dir: Path) -> list[SyntheticClinicalDocument]:
    return [
        SyntheticClinicalDocument.model_validate(row)
        for row in read_jsonl(source_dir / "clinical_documents.jsonl")
    ]


def load_source_annotations(source_dir: Path) -> list[DocumentAnnotation]:
    return [
        DocumentAnnotation.model_validate(row)
        for row in read_jsonl(source_dir / "document_annotations.jsonl")
    ]
