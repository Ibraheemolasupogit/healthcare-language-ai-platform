"""Typed contracts for local preprocessing evidence and Databricks planning."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class PreprocessingBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreprocessingMode(StrEnum):
    CONSERVATIVE = "conservative"
    ANALYTICAL = "analytical"


class PreprocessingRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ProcessedClinicalDocument(PreprocessingBaseModel):
    document_id: str
    synthetic_subject_id: str
    synthetic_encounter_id: str
    document_type: str
    source_text: str
    normalised_text: str
    analytical_text: str | None = None
    preprocessing_mode: PreprocessingMode
    source_character_count: int = Field(ge=0)
    normalised_character_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    unique_token_count: int = Field(ge=0)
    line_count: int = Field(ge=0)
    empty_line_count: int = Field(ge=0)
    uppercase_ratio: float = Field(ge=0)
    digit_ratio: float = Field(ge=0)
    whitespace_ratio: float = Field(ge=0)
    contains_replacement_character: bool
    source_record_checksum: str
    normalised_text_checksum: str
    analytical_text_checksum: str | None = None
    ingestion_run_id: str
    preprocessing_run_id: str
    preprocessed_at: datetime
    normalisation_version: str
    section_parser_version: str
    sentence_segmenter_version: str
    tokeniser_version: str
    quality_rules_version: str

    @field_validator("preprocessed_at")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "preprocessed_at")


class ProcessedSection(PreprocessingBaseModel):
    section_id: str
    document_id: str
    section_index: int = Field(ge=1)
    section_label: str
    normalised_section_label: str
    heading_start: int = Field(ge=0)
    heading_end: int = Field(ge=0)
    content_start: int = Field(ge=0)
    content_end: int = Field(ge=0)
    section_text: str
    section_text_checksum: str
    parser_rule: str
    preprocessing_run_id: str


class ProcessedSentence(PreprocessingBaseModel):
    sentence_id: str
    document_id: str
    section_id: str
    sentence_index: int = Field(ge=1)
    document_sentence_index: int = Field(ge=1)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    sentence_text: str
    sentence_text_checksum: str
    token_count: int = Field(ge=0)
    contains_negation_marker: bool
    contains_numeric_value: bool
    contains_synthetic_identifier: bool
    boundary_rule: str
    preprocessing_run_id: str


class ProjectedAnnotation(PreprocessingBaseModel):
    projection_id: str
    annotation_id: str
    document_id: str
    annotation_type: str
    label: str
    value: str
    source_start: int | None = None
    source_end: int | None = None
    target_start: int | None = None
    target_end: int | None = None
    projection_status: Literal["projected", "unchanged", "unresolved", "not_applicable"]
    projection_rule: str
    preprocessing_run_id: str


class TextTransformation(PreprocessingBaseModel):
    transformation_name: str
    transformation_version: str
    applied: bool
    change_count: int = Field(ge=0)
    before_checksum: str
    after_checksum: str


class DocumentQualityMetric(PreprocessingBaseModel):
    document_id: str
    check_name: str
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    observed_value: str
    threshold: str
    message: str
    preprocessing_run_id: str


class PreprocessingReconciliationMetric(PreprocessingBaseModel):
    metric_name: str
    expected_value: int | str | bool
    actual_value: int | str | bool
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    message: str


class PreprocessingReconciliationReport(PreprocessingBaseModel):
    reconciliation_schema_version: str
    preprocessing_run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[PreprocessingReconciliationMetric]


class DocumentQualityReport(PreprocessingBaseModel):
    quality_schema_version: str
    preprocessing_run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[DocumentQualityMetric]


class DatabricksColumnContract(PreprocessingBaseModel):
    column_name: str
    spark_type: str
    nullable: bool
    natural_key: bool
    source_field: str
    description: str
    governance_classification: str
    partition_recommendation: str | None = None


class DatabricksTableContract(PreprocessingBaseModel):
    table_name: str
    medallion_layer: Literal["bronze", "silver", "gold"]
    description: str
    columns: list[DatabricksColumnContract]


class DatabricksNotebookContract(PreprocessingBaseModel):
    notebook_name: str
    purpose: str
    inputs: list[str]
    outputs: list[str]
    validation_gates: list[str]


class DatabricksJobContract(PreprocessingBaseModel):
    job_name: str
    task_order: list[str]
    retry_policy: str
    timeout_policy: str
    execution_permitted: bool


class DatabricksPipelinePlan(PreprocessingBaseModel):
    plan_schema_version: str
    preprocessing_run_id: str
    source_files: list[str]
    target_medallion_layers: list[str]
    target_table_contracts: list[DatabricksTableContract]
    notebook_task_sequence: list[DatabricksNotebookContract]
    job_contract: DatabricksJobContract
    expected_record_counts: dict[str, int]
    expected_checksums: dict[str, str]
    quality_gates: dict[str, str]
    required_target_state_permissions: list[str]
    dry_run_status: Literal["validated"]
    connection_attempted: bool
    execution_permitted: bool


class PreprocessingManifest(PreprocessingBaseModel):
    manifest_schema_version: str
    preprocessing_contract_version: str
    preprocessing_run_id: str
    preprocessing_mode: PreprocessingMode
    run_status: PreprocessingRunStatus
    source_ingestion_run_id: str
    source_ingestion_manifest_checksum: str
    source_document_count: int
    source_annotation_count: int
    processed_document_count: int
    section_count: int
    sentence_count: int
    projected_annotation_count: int
    unresolved_annotation_count: int
    warning_count: int
    failure_count: int
    total_lexical_token_count: int
    normalisation_version: str
    section_parser_version: str
    sentence_segmenter_version: str
    tokeniser_version: str
    quality_rules_version: str
    databricks_contract_version: str
    reference_timestamp: datetime
    writer_versions: dict[str, str]
    output_files: list[str]
    output_file_checksums: dict[str, str]
    document_type_counts: dict[str, int]
    section_label_counts: dict[str, int]
    quality_status_counts: dict[str, int]
    annotation_projection_status_counts: dict[str, int]
    synthetic_data_only: bool
    clinical_use_prohibited: bool
    reconciliation_status: Literal["passed", "warning", "failed"]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")
