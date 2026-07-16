"""Typed contracts for Milestone 7 retrieval quality evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class QualityBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    NOT_REQUESTED = "not_requested"


class HoldoutDocument(QualityBaseModel):
    document_id: str
    document_type: str
    synthetic_subject_id: str
    synthetic_encounter_id: str
    text: str = Field(min_length=1)
    sections: dict[str, str]
    created_at: datetime
    seed: int
    record_index: int = Field(ge=1)
    template_family: str
    holdout_generator_version: str
    holdout_template_version: str
    holdout_vocabulary_version: str
    synthetic_data_only: bool
    clinical_use_prohibited: bool

    @field_validator("created_at")
    @classmethod
    def created_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "created_at")


class HoldoutAnnotation(QualityBaseModel):
    annotation_id: str
    document_id: str
    synthetic_subject_id: str
    synthetic_encounter_id: str
    annotation_type: str
    value: str
    rationale: str


class VocabularyOverlapReport(QualityBaseModel):
    report_version: str
    original_vocabulary_size: int
    holdout_vocabulary_size: int
    query_vocabulary_size: int
    extraction_vocabulary_size: int
    original_holdout_overlap_ratio: float
    holdout_query_overlap_ratio: float
    extraction_holdout_overlap_ratio: float
    status: Literal["passed", "warning", "failed"]


class HoldoutManifest(QualityBaseModel):
    holdout_dataset_id: str
    schema_version: str
    document_count: int
    document_type_counts: dict[str, int]
    section_count: int
    sentence_count: int
    seed: int
    reference_timestamp: datetime
    holdout_generator_version: str
    holdout_template_version: str
    holdout_vocabulary_version: str
    files: list[str]
    file_checksums: dict[str, str]
    privacy_validation_status: Literal["passed", "warning", "failed"]
    clinical_safety_validation_status: Literal["passed", "warning", "failed"]
    vocabulary_overlap_status: Literal["passed", "warning", "failed"]
    synthetic_data_only: bool
    clinical_use_prohibited: bool

    @field_validator("reference_timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")


class HoldoutQualityReport(QualityBaseModel):
    report_version: str
    validation_status: Literal["passed", "warning", "failed"]
    privacy_validation_status: Literal["passed", "warning", "failed"]
    clinical_safety_validation_status: Literal["passed", "warning", "failed"]
    checks: list[dict[str, str]]


class BenchmarkQuery(QualityBaseModel):
    query_id: str
    query_text: str
    query_category: str
    split: Literal["development", "validation", "holdout"]
    difficulty: str
    leakage_risk: str
    authoring_method: str
    source_overlap_ratio: float = Field(ge=0, le=1)
    holdout_status: Literal["original_fixture", "independent_holdout"]
    target_unit_type: str
    relevant_unit_ids: list[str]
    metadata_filters: dict[str, str]
    polarity_expectation: Literal["affirmed", "negated", "not_applicable"]
    numeric_constraints: list[str]
    benchmark_version: str
    synthetic_data_only: bool


class RelevanceReviewRecord(QualityBaseModel):
    judgment_id: str
    query_id: str
    retrieval_unit_id: str
    relevance_grade: int = Field(ge=0, le=3)
    judgment_status: str
    judgment_source: str
    rationale_code: str
    reviewer_role: str
    reviewed_at: datetime
    benchmark_version: str

    @field_validator("reviewed_at")
    @classmethod
    def reviewed_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reviewed_at")


class BenchmarkSplit(QualityBaseModel):
    split_version: str
    development_query_ids: list[str]
    validation_query_ids: list[str]
    holdout_query_ids: list[str]

    @model_validator(mode="after")
    def splits_must_not_overlap(self) -> BenchmarkSplit:
        dev = set(self.development_query_ids)
        val = set(self.validation_query_ids)
        holdout = set(self.holdout_query_ids)
        if dev & val or dev & holdout or val & holdout:
            raise ValueError("benchmark query splits must not overlap")
        return self


class BenchmarkManifest(QualityBaseModel):
    benchmark_id: str
    benchmark_version: str
    split_version: str
    query_count: int
    relevance_judgment_count: int
    development_query_count: int
    validation_query_count: int
    holdout_query_count: int
    query_category_counts: dict[str, int]
    difficulty_counts: dict[str, int]
    leakage_risk_counts: dict[str, int]
    authoring_method_counts: dict[str, int]
    negation_sensitive_query_count: int
    numeric_detail_query_count: int
    abbreviation_query_count: int
    section_alias_query_count: int
    cross_granularity_query_count: int
    unanswerable_query_count: int
    files: list[str]
    file_checksums: dict[str, str]
    validation_status: Literal["passed", "warning", "failed"]


class QueryExpansionRule(QualityBaseModel):
    expansion_rule_id: str
    original_term: str
    expanded_term: str
    expansion_type: str
    version: str


class ExpandedQuery(QualityBaseModel):
    query_id: str
    original_query_text: str
    expanded_query_text: str
    applied_rules: list[QueryExpansionRule]
    expansion_version: str


class EmbeddingModelMetadata(QualityBaseModel):
    provider_name: str
    provider_version: str
    model_name: str
    model_path: str
    model_checksum: str
    embedding_dimension: int | None
    normalise_embeddings: bool
    batch_size: int
    maximum_sequence_length: int | None
    pooling: str
    availability_status: ModelAvailabilityStatus
    dependency_available: bool
    offline_environment: dict[str, str]
    automatic_download_attempted: bool
    network_connection_attempted: bool


class RetrievalConfiguration(QualityBaseModel):
    configuration_id: str
    name: str
    candidate_strategy: str
    candidate_top_k: int = Field(gt=0)
    embedding_provider: str
    query_expansion_enabled: bool
    negation_features_enabled: bool
    numeric_features_enabled: bool
    abbreviation_expansion_enabled: bool
    section_aliases_enabled: bool
    granularity_policy: str
    reranker: str
    final_top_k: int = Field(gt=0)
    weights: dict[str, float]
    requires_optional_model: bool
    active: bool
    complexity_rank: int = Field(ge=1)


class ConfigurationMetric(QualityBaseModel):
    configuration_id: str
    split: Literal["development", "validation", "holdout"]
    query_group: str
    query_count: int
    hit_rate_at_5: float
    recall_at_5: float
    mrr: float
    ndcg_at_5: float
    zero_hit_query_count: int


class QualityGate(QualityBaseModel):
    gate_id: str
    metric_name: str
    split: str
    query_group: str
    operator: Literal[">=", "<=", "=="]
    threshold: float
    required: bool


class QualityGateResult(QualityBaseModel):
    gate_id: str
    metric_name: str
    split: str
    query_group: str
    operator: str
    threshold: float
    actual_value: float
    status: Literal["passed", "failed"]
    required: bool
    message: str


class RetrievalExperimentManifest(QualityBaseModel):
    experiment_id: str
    configuration_id: str
    benchmark_id: str
    configuration_registry_version: str
    reference_timestamp: datetime
    candidate_strategy: str
    embedding_provider: str
    query_expansion_enabled: bool
    negation_features_enabled: bool
    numeric_features_enabled: bool
    granularity_policy: str
    reranker: str
    development_hit_rate_at_5: float
    validation_hit_rate_at_5: float
    validation_recall_at_5: float
    validation_mrr: float
    validation_ndcg_at_5: float
    paraphrased_hit_rate_at_5: float
    negation_sensitive_hit_rate_at_5: float
    zero_hit_query_count: int
    quality_gate_status: Literal["passed", "failed"]
    files: list[str]
    file_checksums: dict[str, str]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")


class ConfigurationRanking(QualityBaseModel):
    rank: int
    configuration_id: str
    dependency_profile: str
    validation_ndcg_at_5: float
    validation_recall_at_5: float
    validation_mrr: float
    validation_hit_rate_at_5: float
    negation_hit_rate_at_5: float
    paraphrased_hit_rate_at_5: float
    zero_hit_query_count: int
    quality_gate_status: str
    selection_status: str


class SelectedBaseline(QualityBaseModel):
    selected_configuration_id: str
    selection_status: Literal["selected", "not_selected"]
    selection_reason: str
    primary_metric: str
    secondary_metrics: dict[str, float]
    quality_gate_status: Literal["passed", "failed"]
    dependency_profile: str
    embedding_provider: str
    requires_optional_model: bool
    approved_index_id: str
    approved_retrieval_parameters: dict[str, str | int | float | bool]
    known_failures: list[str]
    future_remediation: list[str]


class RetrievalApprovalDecision(QualityBaseModel):
    approval_status: Literal["approved_for_rag_prototype", "conditionally_approved", "not_approved"]
    approved_for_future_rag_prototype: bool
    selected_configuration_id: str
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    known_failing_query_groups: list[str]
    decision_reason: str


class RetrievalComparisonManifest(QualityBaseModel):
    comparison_id: str
    retrieval_comparison_contract_version: str
    benchmark_id: str
    configuration_registry_version: str
    configurations_evaluated: list[str]
    configurations_skipped: list[str]
    selected_configuration_id: str
    selection_metric: str
    holdout_hit_rate_at_5: float
    holdout_recall_at_5: float
    holdout_mrr: float
    holdout_ndcg_at_5: float
    approval_status: str
    reference_timestamp: datetime
    files: list[str]
    file_checksums: dict[str, str]
    reconciliation_status: Literal["passed", "warning", "failed"]

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")


class ReviewerPackManifest(QualityBaseModel):
    reviewer_pack_id: str
    benchmark_id: str
    query_count: int
    relevance_judgment_count: int
    files: list[str]
    file_checksums: dict[str, str]
    reviewer_roles: list[str]
    clinician_validation_claimed: bool
