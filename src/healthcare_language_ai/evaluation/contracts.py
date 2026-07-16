"""Typed contracts for deterministic baseline evaluation evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class EvaluationBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class EvaluationMatch(EvaluationBaseModel):
    match_id: str
    document_id: str
    label: str
    prediction_id: str | None = None
    ground_truth_annotation_id: str | None = None
    match_type: Literal["true_positive", "false_positive", "false_negative"]
    matching_policy: str
    start_offset: int | None = None
    end_offset: int | None = None
    evaluation_run_id: str


class EntityEvaluationMetric(EvaluationBaseModel):
    metric_scope: str
    scope_value: str
    true_positive_count: int = Field(ge=0)
    false_positive_count: int = Field(ge=0)
    false_negative_count: int = Field(ge=0)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    support: int = Field(ge=0)
    evaluation_run_id: str


class ClassificationEvaluationMetric(EvaluationBaseModel):
    class_label: str
    true_positive_count: int = Field(ge=0)
    false_positive_count: int = Field(ge=0)
    false_negative_count: int = Field(ge=0)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1: float = Field(ge=0, le=1)
    support: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)
    evaluation_run_id: str


class ConfusionMatrixRecord(EvaluationBaseModel):
    actual_document_type: str
    predicted_document_type: str
    count: int = Field(ge=0)
    evaluation_run_id: str


class ErrorAnalysisRecord(EvaluationBaseModel):
    error_id: str
    document_id: str
    document_type: str
    label: str
    error_type: str
    prediction_id: str | None = None
    ground_truth_annotation_id: str | None = None
    predicted_value: str | None = None
    expected_value: str | None = None
    predicted_start: int | None = None
    predicted_end: int | None = None
    expected_start: int | None = None
    expected_end: int | None = None
    section_label: str | None = None
    sentence_id: str | None = None
    rule_id: str | None = None
    sanitised_context: str
    context_checksum: str
    likely_reason: str
    evaluation_run_id: str


class EvaluationReconciliationMetric(EvaluationBaseModel):
    metric_name: str
    expected_value: int | str | bool
    actual_value: int | str | bool
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    message: str


class EvaluationReconciliationReport(EvaluationBaseModel):
    reconciliation_schema_version: str
    evaluation_run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[EvaluationReconciliationMetric]


class BaselineModelCard(EvaluationBaseModel):
    model_name: str
    model_version: str
    model_type: str
    purpose: str
    intended_use: str
    out_of_scope_use: str
    training_data: str
    evaluation_data: str
    rule_and_vocabulary_sources: str
    input_contract: str
    output_contract: str
    supported_labels: list[str]
    metrics: dict[str, float]
    known_limitations: list[str]
    synthetic_data_limitation: str
    benchmark_leakage: str
    clinical_safety_limitations: str
    fairness_limitations: str
    privacy_position: str
    failure_modes: list[str]
    human_review_expectations: str
    monitoring_recommendations: str
    future_model_comparison_plan: str


class MLflowExperimentPlan(EvaluationBaseModel):
    plan_schema_version: str
    mlflow_contract_version: str
    experiment_name_placeholder: str
    run_name: str
    extraction_run_id: str
    evaluation_run_id: str
    parameters: dict[str, str]
    metrics_to_log: dict[str, float]
    tags: dict[str, str]
    artifacts_to_log: list[str]
    dataset_lineage: dict[str, str]
    rule_versions: dict[str, str]
    target_registry_stage_placeholder: str
    dry_run_status: Literal["validated"]
    connection_attempted: bool
    execution_permitted: bool


class EvaluationManifest(EvaluationBaseModel):
    manifest_schema_version: str
    evaluation_contract_version: str
    evaluation_run_id: str
    run_status: EvaluationRunStatus
    source_extraction_run_id: str
    source_extraction_manifest_checksum: str
    ground_truth_source: str
    ground_truth_checksum: str
    matching_policy: str
    relaxed_overlap_threshold: float = Field(ge=0, le=1)
    evaluated_document_count: int
    evaluated_ground_truth_count: int
    evaluated_prediction_count: int
    excluded_ground_truth_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    micro_precision: float = Field(ge=0, le=1)
    micro_recall: float = Field(ge=0, le=1)
    micro_f1: float = Field(ge=0, le=1)
    macro_precision: float = Field(ge=0, le=1)
    macro_recall: float = Field(ge=0, le=1)
    macro_f1: float = Field(ge=0, le=1)
    classification_accuracy: float = Field(ge=0, le=1)
    classification_macro_f1: float = Field(ge=0, le=1)
    error_count: int
    metrics_version: str
    error_analysis_version: str
    mlflow_contract_version: str
    reference_timestamp: datetime
    output_files: list[str]
    output_file_checksums: dict[str, str]
    synthetic_data_only: bool
    clinical_use_prohibited: bool
    reconciliation_status: Literal["passed", "warning", "failed"]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")
