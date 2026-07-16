"""Pydantic domain contracts for later milestones."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from healthcare_language_ai.domain.enums import (
    ClinicalDocumentType,
    DataClassification,
    PipelineStage,
    ProcessingStatus,
)
from healthcare_language_ai.utils.time import require_timezone_aware, utc_now


class StrictDomainModel(BaseModel):
    """Base model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DocumentMetadata(StrictDomainModel):
    """Safe metadata for synthetic clinical documents."""

    synthetic_subject_id: str | None = None
    synthetic_encounter_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)


class ClinicalDocument(StrictDomainModel):
    """Synthetic document contract with no direct patient identifiers."""

    document_id: str = Field(min_length=1)
    document_type: ClinicalDocumentType
    text: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    source_system: str = Field(default="synthetic_local", min_length=1)
    data_classification: DataClassification = DataClassification.SYNTHETIC
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "created_at")

    @field_validator("data_classification")
    @classmethod
    def prohibit_unsupported_real_patient_data(
        cls, value: DataClassification
    ) -> DataClassification:
        if value is not DataClassification.SYNTHETIC:
            msg = "Milestone 1 accepts synthetic documents only"
            raise ValueError(msg)
        return value


class ProcessingRecord(StrictDomainModel):
    """Audit-oriented record for future pipeline stage execution."""

    record_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    stage: PipelineStage
    status: ProcessingStatus = ProcessingStatus.PENDING
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    message: str | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return require_timezone_aware(value, "timestamp")

    @model_validator(mode="after")
    def completed_at_cannot_precede_started_at(self) -> ProcessingRecord:
        if self.completed_at is not None and self.completed_at < self.started_at:
            msg = "completed_at cannot be before started_at"
            raise ValueError(msg)
        return self


class PipelineRun(StrictDomainModel):
    """Reproducibility contract for future pipeline runs."""

    run_id: str = Field(min_length=1)
    pipeline_name: str = Field(min_length=1)
    pipeline_version: str = Field(min_length=1)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    input_count: int = Field(default=0, ge=0)
    output_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    configuration_hash: str | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        return require_timezone_aware(value, "timestamp")

    @model_validator(mode="after")
    def completed_at_cannot_precede_started_at(self) -> PipelineRun:
        if self.completed_at is not None and self.completed_at < self.started_at:
            msg = "completed_at cannot be before started_at"
            raise ValueError(msg)
        return self
