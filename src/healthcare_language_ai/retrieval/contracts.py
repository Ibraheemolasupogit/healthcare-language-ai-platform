"""Typed contracts for local retrieval indexes, runs and evaluations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from healthcare_language_ai.utils.time import require_timezone_aware


class RetrievalBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class RetrievalUnitType(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    SENTENCE = "sentence"


class RetrievalStrategy(StrEnum):
    KEYWORD = "keyword"
    TFIDF = "tfidf"
    BM25 = "bm25"
    HYBRID = "hybrid"


class EmbeddingProvider(StrEnum):
    DETERMINISTIC_HASH = "deterministic_hash"
    SENTENCE_TRANSFORMER = "sentence_transformer"


class RetrievalUnit(RetrievalBaseModel):
    retrieval_unit_id: str
    document_id: str
    section_id: str | None = None
    sentence_id: str | None = None
    unit_type: RetrievalUnitType
    document_type: str
    section_label: str | None = None
    text: str
    text_checksum: str
    token_count: int = Field(ge=0)
    synthetic_subject_id: str
    synthetic_encounter_id: str
    source_preprocessing_run_id: str
    source_extraction_run_id: str
    corpus_version: str


class CorpusStatistics(RetrievalBaseModel):
    document_count: int
    section_count: int
    sentence_count: int
    retrieval_unit_count: int
    token_count: int
    unique_token_count: int
    document_type_distribution: dict[str, int]
    section_label_distribution: dict[str, int]
    unit_type_distribution: dict[str, int]
    average_unit_length: float
    minimum_unit_length: int
    maximum_unit_length: int


class IndexManifest(RetrievalBaseModel):
    manifest_schema_version: str
    retrieval_contract_version: str
    index_id: str
    run_status: RetrievalRunStatus
    source_preprocessing_run_id: str
    source_preprocessing_manifest_checksum: str
    source_extraction_run_id: str
    source_extraction_manifest_checksum: str
    corpus_version: str
    unit_types: list[str]
    text_representation: Literal["normalised_text"]
    retrieval_unit_count: int
    document_count: int
    section_count: int
    sentence_count: int
    token_count: int
    vocabulary_size: int
    index_strategies: list[str]
    embedding_provider: EmbeddingProvider
    embedding_dimension: int
    tokeniser_version: str
    keyword_version: str
    tfidf_version: str
    bm25_version: str
    hash_embedding_version: str
    hybrid_version: str
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


class RetrievalReconciliationMetric(RetrievalBaseModel):
    metric_name: str
    expected_value: int | str | bool
    actual_value: int | str | bool
    status: Literal["passed", "warning", "failed"]
    severity: Literal["info", "warning", "error"]
    message: str


class RetrievalReconciliationReport(RetrievalBaseModel):
    reconciliation_schema_version: str
    run_id: str
    overall_status: Literal["passed", "warning", "failed"]
    metrics: list[RetrievalReconciliationMetric]


class RetrievalQuery(RetrievalBaseModel):
    query_id: str
    query_text: str
    query_category: str
    target_unit_type: str
    relevant_document_ids: list[str]
    relevant_section_ids: list[str]
    relevant_sentence_ids: list[str]
    metadata_filters: dict[str, str]
    difficulty: str
    generation_method: str
    leakage_risk: str
    query_version: str
    synthetic_data_only: bool


class RelevanceJudgment(RetrievalBaseModel):
    judgment_id: str
    query_id: str
    retrieval_unit_id: str
    relevance_grade: int = Field(ge=0, le=2)
    judgment_source: str
    query_version: str


class RetrievalResult(RetrievalBaseModel):
    retrieval_run_id: str
    query_id: str
    rank: int = Field(ge=1)
    retrieval_unit_id: str
    document_id: str
    section_id: str | None = None
    sentence_id: str | None = None
    unit_type: str
    document_type: str
    section_label: str | None = None
    score: float
    keyword_score: float
    tfidf_score: float
    bm25_score: float
    dense_score: float
    metadata_score: float
    fusion_score: float
    matched_terms: str
    text_checksum: str
    sanitised_snippet: str
    relevant: bool
    relevance_grade: int = Field(ge=0, le=2)


class RetrievalManifest(RetrievalBaseModel):
    manifest_schema_version: str
    retrieval_contract_version: str
    retrieval_run_id: str
    run_status: RetrievalRunStatus
    index_id: str
    index_manifest_checksum: str
    query_set_checksum: str
    strategy: RetrievalStrategy
    top_k: int
    query_count: int
    returned_result_count: int
    zero_result_query_count: int
    metadata_filtered_query_count: int
    filter_policy: str
    score_normalisation_version: str
    fusion_version: str
    fusion_weights: dict[str, float]
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


class RetrievalMetric(RetrievalBaseModel):
    metric_scope: str
    scope_value: str
    k: int
    query_count: int
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    mrr: float
    map_score: float
    ndcg_at_k: float
    zero_hit_query_count: int
    average_relevant_rank: float
    retrieval_evaluation_run_id: str


class RetrievalFailureRecord(RetrievalBaseModel):
    failure_id: str
    query_id: str
    query_category: str
    strategy: str
    failure_type: str
    expected_unit_id: str | None = None
    returned_unit_id: str | None = None
    expected_rank: int | None = None
    actual_rank: int | None = None
    relevant_score: float | None = None
    top_result_score: float | None = None
    matched_terms: str
    sanitised_query: str
    sanitised_result_snippet: str
    likely_reason: str
    retrieval_evaluation_run_id: str


class RetrievalEvaluationManifest(RetrievalBaseModel):
    manifest_schema_version: str
    retrieval_evaluation_contract_version: str
    retrieval_evaluation_run_id: str
    run_status: RetrievalRunStatus
    retrieval_run_id: str
    retrieval_manifest_checksum: str
    relevance_judgment_checksum: str
    evaluated_query_count: int
    k_values: list[int]
    precision_at_1: float
    precision_at_5: float
    recall_at_5: float
    hit_rate_at_1: float
    hit_rate_at_5: float
    mrr: float
    map_score: float
    ndcg_at_5: float
    zero_hit_query_count: int
    failure_count: int
    retrieval_metrics_version: str
    retrieval_failure_version: str
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


class RetrievalModelCard(RetrievalBaseModel):
    system_name: str
    version: str
    retrieval_strategies: list[str]
    corpus_source: str
    corpus_size: int
    retrieval_units: dict[str, int]
    tokenisation: str
    sparse_features: str
    dense_vector_method: str
    hybrid_fusion: str
    query_set_construction: str
    evaluation_metrics: dict[str, float]
    performance_by_query_group: dict[str, float]
    benchmark_leakage: str
    known_limitations: list[str]
    clinical_safety_position: str
    privacy_position: str
    unsupported_uses: list[str]
    failure_modes: list[str]
    human_review_expectations: str
    future_dense_model_comparison: str


class VectorSearchPlan(RetrievalBaseModel):
    plan_schema_version: str
    vector_search_contract_version: str
    endpoint_placeholder: str
    index_placeholder: str
    primary_key: str
    embedding_column: str
    embedding_dimension: int
    metadata_filter_columns: list[str]
    sync_strategy: str
    access_control_expectations: list[str]
    source_index_id: str
    dry_run_status: Literal["validated"]
    connection_attempted: bool
    execution_permitted: bool
