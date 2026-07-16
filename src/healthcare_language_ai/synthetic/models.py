"""Pydantic models for persisted synthetic dataset evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from healthcare_language_ai.domain.enums import ClinicalDocumentType, DataClassification
from healthcare_language_ai.utils.time import require_timezone_aware


class SyntheticBaseModel(BaseModel):
    """Base model for stable JSON serialization."""

    model_config = ConfigDict(extra="forbid")


class SyntheticDocumentMetadata(SyntheticBaseModel):
    synthetic_subject_id: str
    synthetic_encounter_id: str
    encounter_context: str
    specialty: str | None = None
    body_site: str | None = None
    presenting_concern: str | None = None
    investigation: str | None = None
    administrative_priority: str | None = None
    workflow_status: str


class SyntheticClinicalDocument(SyntheticBaseModel):
    document_id: str
    document_type: ClinicalDocumentType
    text: str = Field(min_length=1)
    created_at: datetime
    encounter_started_at: datetime
    encounter_ended_at: datetime
    source_system: str = "synthetic_generator"
    data_classification: DataClassification = DataClassification.SYNTHETIC
    metadata: SyntheticDocumentMetadata
    generator_version: str
    template_name: str
    template_version: str
    vocabulary_version: str
    seed: int
    record_index: int = Field(ge=1)

    @field_validator("created_at", "encounter_started_at", "encounter_ended_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "synthetic timestamp")

    @field_validator("data_classification")
    @classmethod
    def classification_must_be_synthetic(cls, value: DataClassification) -> DataClassification:
        if value is not DataClassification.SYNTHETIC:
            msg = "generated records must be synthetic"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def timestamps_must_be_chronological(self) -> SyntheticClinicalDocument:
        if self.encounter_started_at > self.encounter_ended_at:
            msg = "encounter_started_at cannot be after encounter_ended_at"
            raise ValueError(msg)
        if self.created_at < self.encounter_started_at:
            msg = "created_at cannot be before encounter_started_at"
            raise ValueError(msg)
        return self


class EntityAnnotation(SyntheticBaseModel):
    label: str
    value: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    normalised_value: str
    source: Literal["template"] = "template"

    @model_validator(mode="after")
    def end_must_follow_start(self) -> EntityAnnotation:
        if self.end <= self.start:
            msg = "annotation end must be greater than start"
            raise ValueError(msg)
        return self


class DocumentAnnotation(SyntheticBaseModel):
    document_id: str
    synthetic_subject_id: str
    synthetic_encounter_id: str
    document_type: ClinicalDocumentType
    entities: list[EntityAnnotation] = Field(default_factory=list)
    document_level: dict[str, str] = Field(default_factory=dict)


class SyntheticDocumentRecord(SyntheticBaseModel):
    document: SyntheticClinicalDocument
    annotation: DocumentAnnotation


class DatasetManifest(SyntheticBaseModel):
    dataset_name: str
    dataset_version: str
    generator_version: str
    template_version: str
    vocabulary_version: str
    seed: int
    reference_timestamp: datetime
    record_count: int = Field(ge=0)
    document_type_counts: dict[str, int]
    annotation_label_counts: dict[str, int]
    files: list[str]
    file_checksums: dict[str, str]
    schema_version: str
    synthetic_data_only: bool
    clinical_use_prohibited: bool

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")


class ValidationCheck(SyntheticBaseModel):
    name: str
    status: Literal["passed", "warning", "failed"]
    message: str
    severity: Literal["info", "warning", "error"] = "info"


class DataQualityReport(SyntheticBaseModel):
    dataset_name: str
    schema_version: str
    validation_status: Literal["passed", "warning", "failed"]
    checks: list[ValidationCheck]
    record_count: int
    document_type_counts: dict[str, int]
    annotation_label_counts: dict[str, int]
    synthetic_data_only: bool
    clinical_use_prohibited: bool


class SyntheticDataset(SyntheticBaseModel):
    records: list[SyntheticDocumentRecord]
    manifest: DatasetManifest | None = None
    quality_report: DataQualityReport | None = None
