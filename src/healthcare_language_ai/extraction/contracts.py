"""Typed contracts for deterministic rule-based extraction evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class ExtractionBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractionRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class PredictionScope(StrEnum):
    SPAN = "span"
    DOCUMENT = "document"
    SECTION = "section"


SUPPORTED_ENTITY_LABELS = {
    "administrative_priority",
    "body_site",
    "descriptor",
    "encounter_context",
    "investigation",
    "observation",
    "presenting_concern",
    "specialty",
    "workflow_status",
}

SUPPORTED_DOCUMENT_TYPES = {
    "clinical_note",
    "discharge_summary",
    "pathology_report",
    "radiology_report",
    "referral_letter",
}


class VocabularyEntry(ExtractionBaseModel):
    vocabulary_entry_id: str
    canonical_value: str
    surface_forms: list[str]
    label: str
    document_types: list[str]
    section_labels: list[str]
    case_sensitive: bool
    word_boundary_required: bool
    priority: int = Field(ge=0)
    active: bool
    vocabulary_version: str


class ExtractionRule(ExtractionBaseModel):
    rule_id: str
    label: str
    vocabulary_entry_id: str
    rule_version: str
    priority: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class RuleMatch(ExtractionBaseModel):
    candidate_id: str
    document_id: str
    label: str
    value: str
    normalised_value: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    matched_text: str
    section_id: str
    section_label: str
    sentence_id: str
    rule_id: str
    rule_version: str
    vocabulary_entry_id: str
    vocabulary_version: str
    priority: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    text_representation: Literal["normalised_text"]
    preprocessing_run_id: str
    extraction_run_id: str


class SuppressedCandidate(ExtractionBaseModel):
    candidate_id: str
    document_id: str
    label: str
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    rule_id: str
    suppressed_by_candidate_id: str
    suppression_reason: str
    extraction_run_id: str


class EntityPrediction(ExtractionBaseModel):
    prediction_id: str
    document_id: str
    label: str
    value: str
    normalised_value: str
    start_offset: int | None = None
    end_offset: int | None = None
    prediction_scope: PredictionScope
    confidence: float = Field(ge=0, le=1)
    rule_id: str
    rule_version: str
    vocabulary_version: str
    matched_text: str
    source_text_representation: Literal["normalised_text"]
    section_id: str | None = None
    sentence_id: str | None = None
    preprocessing_run_id: str
    extraction_run_id: str


class DocumentClassificationPrediction(ExtractionBaseModel):
    document_id: str
    predicted_document_type: str
    confidence: float = Field(ge=0, le=1)
    matched_rule_ids: str
    score_by_class: str
    classification_rule_version: str
    extraction_run_id: str


class SectionClassificationPrediction(ExtractionBaseModel):
    section_id: str
    document_id: str
    predicted_section_label: str
    confidence: float = Field(ge=0, le=1)
    classification_rule_version: str
    extraction_run_id: str


class CandidateSummary(ExtractionBaseModel):
    extraction_run_id: str
    candidate_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    suppressed_overlap_count: int = Field(ge=0)
    duplicate_prediction_count: int = Field(ge=0)
    candidate_count_by_label: dict[str, int]
    accepted_count_by_label: dict[str, int]


class PredictionReconciliationMetric(ExtractionBaseModel):
    metric_name: str
    expected_value: int | str | bool
    actual_value: int | str | bool
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    message: str


class PredictionReconciliationReport(ExtractionBaseModel):
    reconciliation_schema_version: str
    extraction_run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[PredictionReconciliationMetric]


class ExtractionManifest(ExtractionBaseModel):
    manifest_schema_version: str
    extraction_contract_version: str
    extraction_run_id: str
    run_status: ExtractionRunStatus
    source_preprocessing_run_id: str
    source_preprocessing_manifest_checksum: str
    source_document_count: int
    source_section_count: int
    source_sentence_count: int
    source_annotation_count: int
    entity_prediction_count: int
    document_classification_count: int
    section_classification_count: int
    candidate_count: int
    suppressed_overlap_count: int
    duplicate_prediction_count: int
    prediction_scope_counts: dict[str, int]
    prediction_label_counts: dict[str, int]
    document_type_prediction_counts: dict[str, int]
    entity_rule_version: str
    classification_rule_version: str
    overlap_resolution_version: str
    vocabulary_version: str
    text_representation: Literal["normalised_text"]
    reference_timestamp: datetime
    writer_versions: dict[str, str]
    output_files: list[str]
    output_file_checksums: dict[str, str]
    synthetic_data_only: bool
    clinical_use_prohibited: bool
    reconciliation_status: Literal["passed", "warning", "failed"]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")
