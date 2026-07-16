from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from healthcare_language_ai.domain import (
    ClinicalDocument,
    ClinicalDocumentType,
    DataClassification,
    PipelineRun,
)


def test_clinical_document_defaults_to_synthetic() -> None:
    document = ClinicalDocument(
        document_id="doc-1",
        document_type=ClinicalDocumentType.CLINICAL_NOTE,
        text="Synthetic note text.",
    )
    assert document.data_classification is DataClassification.SYNTHETIC
    assert document.metadata.tags == []


def test_non_empty_clinical_text_validation() -> None:
    with pytest.raises(ValidationError):
        ClinicalDocument(
            document_id="doc-1",
            document_type=ClinicalDocumentType.CLINICAL_NOTE,
            text="",
        )


def test_timezone_aware_timestamp_validation() -> None:
    with pytest.raises(ValidationError):
        ClinicalDocument(
            document_id="doc-1",
            document_type=ClinicalDocumentType.CLINICAL_NOTE,
            text="Synthetic note text.",
            created_at=datetime(2026, 1, 1),
        )


def test_rejects_non_synthetic_document_classification() -> None:
    with pytest.raises(ValidationError):
        ClinicalDocument(
            document_id="doc-1",
            document_type=ClinicalDocumentType.CLINICAL_NOTE,
            text="Synthetic note text.",
            data_classification=DataClassification.PUBLIC,
        )


def test_non_negative_pipeline_counts() -> None:
    with pytest.raises(ValidationError):
        PipelineRun(
            run_id="run-1",
            pipeline_name="foundation",
            pipeline_version="0.1.0",
            input_count=-1,
        )


def test_pipeline_completed_at_cannot_precede_started_at() -> None:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValidationError):
        PipelineRun(
            run_id="run-1",
            pipeline_name="foundation",
            pipeline_version="0.1.0",
            started_at=started,
            completed_at=started - timedelta(seconds=1),
        )
