"""Contracts for Milestone 8 retrieval remediation evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RemediationBaseModel(BaseModel):
    """Strict base model for deterministic evidence files."""

    model_config = ConfigDict(extra="forbid")


class RemediationConfiguration(RemediationBaseModel):
    configuration_id: str
    candidate_retrievers: list[str]
    character_features: list[str] = Field(default_factory=list)
    phrase_features: list[str] = Field(default_factory=list)
    proximity_features: list[str] = Field(default_factory=list)
    synonym_expansion: bool = False
    pseudo_relevance_feedback: bool = False
    entity_features: list[str] = Field(default_factory=list)
    reranker: str = "none"
    diversification: bool = False
    abstention: bool = False
    description: str


class FailureAnalysisManifest(RemediationBaseModel):
    failure_run_id: str
    source_experiment_id: str
    benchmark_id: str
    query_count: int
    successful_query_count: int
    zero_hit_count: int
    below_k_relevant_count: int
    lexical_gap_count: int
    synonym_gap_count: int
    abbreviation_gap_count: int
    phrase_gap_count: int
    negation_conflict_count: int
    numeric_conflict_count: int
    granularity_conflict_count: int
    judgment_ambiguity_count: int
    highest_priority_failure_cohorts: list[str]
    failure_analysis_version: str
    reconciliation_status: str
    output_checksums: dict[str, str]


class BenchmarkUpgradeManifest(RemediationBaseModel):
    benchmark_id: str
    benchmark_version: str
    source_benchmark_version: str
    judgment_version: str
    adjudication_version: str
    query_count: int
    judgment_count: int
    accepted_adjudication_count: int
    rejected_adjudication_count: int
    unresolved_adjudication_count: int
    development_query_count: int
    validation_query_count: int
    holdout_query_count: int
    query_category_counts: dict[str, int]
    authoring_method_counts: dict[str, int]
    paraphrased_query_count: int
    negation_sensitive_query_count: int
    numeric_detail_query_count: int
    unanswerable_query_count: int
    split_overlap_status: str
    original_benchmark_mutation_status: str
    validation_status: str
    output_checksums: dict[str, str]


class RemediationExperimentManifest(RemediationBaseModel):
    experiment_id: str
    configuration_id: str
    benchmark_id: str
    benchmark_version: str
    reference_timestamp: datetime
    candidate_retrievers: list[str]
    character_features: list[str]
    phrase_features: list[str]
    proximity_features: list[str]
    synonym_expansion: bool
    pseudo_relevance_feedback: bool
    entity_features: list[str]
    reranker: str
    diversification: bool
    abstention: bool
    development_hit_rate_at_5: float
    validation_hit_rate_at_5: float
    validation_recall_at_5: float
    validation_mrr: float
    validation_ndcg_at_5: float
    paraphrased_hit_rate_at_5: float
    negation_sensitive_hit_rate_at_5: float
    validation_zero_hit_count: int
    unanswerable_abstention_accuracy: float
    answerable_coverage: float
    quality_gate_status: str
    output_checksums: dict[str, str]


class RemediationComparisonManifest(RemediationBaseModel):
    comparison_id: str
    benchmark_id: str
    benchmark_version: str
    configurations_evaluated: list[str]
    configurations_skipped: list[str]
    selected_configuration_id: str
    primary_metric: str
    validation_hit_rate_at_5: float
    validation_recall_at_5: float
    validation_mrr: float
    validation_ndcg_at_5: float
    paraphrased_hit_rate_at_5: float
    negation_sensitive_hit_rate_at_5: float
    validation_zero_hit_count: int
    holdout_hit_rate_at_5: float
    holdout_recall_at_5: float
    holdout_mrr: float
    holdout_ndcg_at_5: float
    unanswerable_abstention_accuracy: float
    answerable_coverage: float
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    approval_status: str
    approved_for_future_rag_prototype: bool
    known_failing_query_groups: list[str]
    feature_ablation_conclusion: str
    reconciliation_status: str
    output_checksums: dict[str, str]


class RemediationApprovalDecision(RemediationBaseModel):
    selected_configuration_id: str
    approval_status: str
    approved_for_future_rag_prototype: bool
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    required_limitations: list[str]
    mlflow_contract: dict[str, Any]
    databricks_contract: dict[str, Any]
    vector_search_contract: dict[str, Any]
