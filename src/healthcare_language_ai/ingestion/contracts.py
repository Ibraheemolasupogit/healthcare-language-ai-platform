"""Typed contracts for local ingestion evidence and Snowflake planning."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class IngestionBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestionMode(StrEnum):
    STRICT = "strict"
    QUARANTINE = "quarantine"


class IngestionRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_QUARANTINE = "completed_with_quarantine"
    FAILED = "failed"


class OverwritePolicy(StrEnum):
    FAIL_IF_EXISTS = "fail_if_exists"
    REPLACE_IDENTICAL = "replace_identical"
    FORCE_REPLACE = "force_replace"


class IngestionFile(IngestionBaseModel):
    file_name: str
    path: Path
    size_bytes: int
    sha256: str


class IngestionSource(IngestionBaseModel):
    source_dir: Path
    files: list[IngestionFile]
    source_manifest_checksum: str


class CanonicalClinicalDocument(IngestionBaseModel):
    document_id: str
    synthetic_subject_id: str
    synthetic_encounter_id: str
    document_type: str
    source_system: str
    data_classification: str
    document_text: str
    document_created_at: datetime
    encounter_started_at: datetime
    encounter_ended_at: datetime
    generator_version: str
    template_name: str
    template_version: str
    vocabulary_version: str
    source_dataset_name: str
    source_dataset_version: str
    source_seed: int
    source_reference_timestamp: datetime
    source_record_index: int
    source_file: str
    source_line_number: int
    source_record_checksum: str
    ingestion_run_id: str
    ingested_at: datetime

    @field_validator(
        "document_created_at",
        "encounter_started_at",
        "encounter_ended_at",
        "source_reference_timestamp",
        "ingested_at",
    )
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "canonical timestamp")


class CanonicalDocumentAnnotation(IngestionBaseModel):
    annotation_id: str
    document_id: str
    annotation_type: Literal["span", "document_level"]
    label: str
    value: str
    normalised_value: str
    start_offset: int | None = None
    end_offset: int | None = None
    annotation_source: str
    source_annotation_index: int
    source_record_checksum: str
    ingestion_run_id: str


class QuarantineRecord(IngestionBaseModel):
    source_file: str
    source_line_number: int | None = None
    record_identifier: str | None = None
    error_code: str
    error_category: str
    sanitised_error_message: str
    payload_checksum: str
    quarantine_timestamp: datetime

    @field_validator("quarantine_timestamp")
    @classmethod
    def quarantine_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "quarantine_timestamp")


class ReconciliationMetric(IngestionBaseModel):
    metric_name: str
    expected_value: int | str | bool
    actual_value: int | str | bool
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    message: str


class ReconciliationReport(IngestionBaseModel):
    reconciliation_schema_version: str
    ingestion_run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[ReconciliationMetric]


class SnowflakeColumnContract(IngestionBaseModel):
    column_name: str
    snowflake_type: str
    nullable: bool
    key_role: str | None = None
    description: str
    source_field: str
    governance_classification: str


class SnowflakeTableContract(IngestionBaseModel):
    table_name: str
    namespace: str
    description: str
    columns: list[SnowflakeColumnContract]


class SnowflakeLoadPlan(IngestionBaseModel):
    plan_schema_version: str
    snowflake_contract_version: str
    target_database: str
    target_schemas: list[str]
    target_tables: list[SnowflakeTableContract]
    input_files: list[str]
    input_format: dict[str, str]
    expected_row_counts: dict[str, int]
    expected_checksums: dict[str, str]
    column_mappings: dict[str, dict[str, str]]
    copy_into_reference_statements: list[str]
    post_load_validation_queries: list[str]
    required_target_state_role: str
    dry_run_status: Literal["validated"]
    execution_prohibited: bool
    no_connection_attempted: bool


class IngestionManifest(IngestionBaseModel):
    manifest_schema_version: str
    ingestion_contract_version: str
    ingestion_run_id: str
    ingestion_mode: IngestionMode
    run_status: IngestionRunStatus
    source_dataset_name: str
    source_dataset_version: str
    source_manifest_checksum: str
    source_file_checksums: dict[str, str]
    source_record_count: int
    source_annotation_count: int
    canonical_document_count: int
    canonical_annotation_count: int
    quarantine_count: int
    duplicate_count: int
    orphan_annotation_count: int
    generator_version: str
    template_version: str
    vocabulary_version: str
    reference_timestamp: datetime
    writer_versions: dict[str, str]
    output_files: list[str]
    output_file_checksums: dict[str, str]
    snowflake_contract_version: str
    synthetic_data_only: bool
    clinical_use_prohibited: bool
    document_type_counts: dict[str, int] = Field(default_factory=dict)
    annotation_label_counts: dict[str, int] = Field(default_factory=dict)
    reconciliation_status: Literal["passed", "warning", "failed"]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")
