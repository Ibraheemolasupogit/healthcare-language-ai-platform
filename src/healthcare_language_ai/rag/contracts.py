"""Pydantic contracts for guarded synthetic RAG evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RagBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuerySafetyClassification(RagBaseModel):
    query_id: str
    category: str
    allowed_for_retrieval: bool
    refusal_reason: str = ""
    safety_version: str = "1.0.0"


class RagQuery(RagBaseModel):
    query_id: str
    source_query_id: str = ""
    query_text: str
    query_category: str
    split: str
    difficulty: str = "medium"
    leakage_risk: str = "medium"
    expected_answer_status: str
    synthetic_context_required: bool = True
    metadata_filters: dict[str, str] = Field(default_factory=dict)
    required_evidence_unit_ids: list[str] = Field(default_factory=list)
    acceptable_evidence_unit_ids: list[str] = Field(default_factory=list)


class RagExpectedOutcome(RagBaseModel):
    query_id: str
    expected_answer_status: str
    required_evidence_unit_ids: list[str] = Field(default_factory=list)
    acceptable_evidence_unit_ids: list[str] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)
    prohibited_facts: list[str] = Field(default_factory=list)
    expected_citation_min: int = 0
    expected_citation_max: int = 5
    expected_refusal_reason: str = ""
    expected_safety_outcome: str = "passed"


class EvidenceUnit(RagBaseModel):
    evidence_id: str
    retrieval_unit_id: str
    document_id: str
    section_id: str = ""
    sentence_id: str = ""
    unit_type: str
    rank: int
    retrieval_score: float
    retrieval_confidence: float
    text: str
    text_checksum: str
    bounded_snippet: str
    source_preprocessing_run_id: str
    source_extraction_run_id: str
    source_index_id: str
    citation_label: str


class EvidenceExclusion(RagBaseModel):
    retrieval_unit_id: str
    reason: str


class EvidenceBundle(RagBaseModel):
    evidence_bundle_id: str
    query_id: str
    query_text_checksum: str
    retrieval_run_id: str
    retrieval_configuration_id: str
    retrieval_approval_id: str
    retrieval_status: str
    retrieval_confidence: float
    selected_unit_count: int
    selected_document_count: int
    selected_section_count: int
    selected_sentence_count: int
    total_character_count: int
    total_token_count: int
    evidence_units: list[EvidenceUnit]
    excluded_units: list[EvidenceExclusion]
    context_checksum: str
    assembly_version: str = "1.0.0"


class PromptContract(RagBaseModel):
    prompt_id: str
    prompt_version: str
    purpose: str
    allowed_input_fields: list[str]
    required_output_fields: list[str]
    citation_format: str
    refusal_rules: list[str]
    prohibited_content: list[str]
    maximum_context_size: int
    maximum_answer_size: int
    safety_disclaimer: str


class GenerationConfiguration(RagBaseModel):
    provider_name: str
    provider_version: str
    model_name: str
    model_path: str = ""
    model_checksum: str = ""
    generation_mode: str
    maximum_input_tokens: int = 2000
    maximum_output_tokens: int = 180
    temperature: float = 0.0
    top_p: float = 1.0
    seed: int = 9026


class GeneratorMetadata(RagBaseModel):
    provider_name: str
    provider_version: str
    generation_mode: str
    automatic_download_attempted: bool = False
    network_connection_attempted: bool = False


class RagClaim(RagBaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    sentence_index: int
    support_status: str
    supporting_citation_ids: list[str] = Field(default_factory=list)
    unsupported_reason: str = ""
    safety_status: str = "passed"


class RagCitation(RagBaseModel):
    citation_id: str
    citation_label: str
    evidence_id: str
    retrieval_unit_id: str
    document_id: str
    section_id: str = ""
    sentence_id: str = ""
    claim_ids: list[str]
    quoted_span: str
    quoted_span_start: int
    quoted_span_end: int
    source_text_checksum: str
    citation_status: str


class RagAnswer(RagBaseModel):
    answer_id: str
    rag_run_id: str
    query_id: str
    answer_status: str
    answer_text: str
    answer_text_checksum: str
    citations: list[RagCitation]
    claims: list[RagClaim]
    refusal_reason: str
    retrieval_status: str
    retrieval_confidence: float
    generator_provider: str
    generator_version: str
    prompt_id: str
    prompt_version: str
    synthetic_data_only: bool = True
    clinical_use_prohibited: bool = True
    created_at: datetime


class CitationValidationResult(RagBaseModel):
    answer_id: str
    query_id: str
    citation_validity_status: str
    invalid_citation_count: int
    claims_with_citations: int
    claims_without_citations: int
    validation_version: str = "1.0.0"


class ClaimGroundingResult(RagBaseModel):
    claim_id: str
    grounding_status: str
    support_score: float
    evidence_ids: list[str]


class GroundednessReport(RagBaseModel):
    answer_id: str
    query_id: str
    groundedness_status: str
    supported_claim_count: int
    partially_supported_claim_count: int
    unsupported_claim_count: int
    numeric_consistency_status: str
    negation_consistency_status: str
    claim_results: list[ClaimGroundingResult]
    groundedness_version: str = "1.0.0"


class SafetyValidationResult(RagBaseModel):
    answer_id: str
    query_id: str
    safety_status: str
    violation_count: int
    prohibited_patterns: list[str] = Field(default_factory=list)
    safety_rules_version: str = "1.0.0"


class RagRun(RagBaseModel):
    rag_run_id: str
    retrieval_approval_id: str
    retrieval_configuration_id: str
    generator_provider: str
    generator_version: str
    prompt_contract_version: str


class RagManifest(RagBaseModel):
    rag_run_id: str
    retrieval_approval_id: str
    retrieval_configuration_id: str
    generator_provider: str
    generator_version: str
    prompt_contract_version: str
    query_count: int
    grounded_answer_count: int
    partial_answer_count: int
    refusal_count: int
    retrieval_abstention_count: int
    unanswerable_refusal_count: int
    unsupported_request_refusal_count: int
    conflicting_evidence_count: int
    citation_validation_failure_count: int
    groundedness_failure_count: int
    safety_validation_failure_count: int
    evidence_unit_count: int
    claim_count: int
    citation_count: int
    reconciliation_status: str
    output_checksums: dict[str, str]


class RagReconciliationMetric(RagBaseModel):
    metric_name: str
    expected: int | str | float
    actual: int | str | float
    status: str


class RagReconciliationReport(RagBaseModel):
    rag_run_id: str
    metrics: list[RagReconciliationMetric]
    reconciliation_status: str


class RagEvaluationCase(RagBaseModel):
    query_id: str
    answer_id: str
    expected_answer_status: str
    actual_answer_status: str
    correct_status: bool
    split: str
    query_category: str


class RagEvaluationMetric(RagBaseModel):
    metric_name: str
    metric_value: float
    numerator: float
    denominator: float


class RagErrorRecord(RagBaseModel):
    error_id: str
    query_id: str
    query_category: str
    answer_id: str
    error_type: str
    claim_id: str = ""
    citation_id: str = ""
    expected_status: str
    actual_status: str
    evidence_ids: list[str] = Field(default_factory=list)
    bounded_query: str
    bounded_answer_excerpt: str
    likely_reason: str
    remediation: str
    evaluation_run_id: str


class RagQualityGate(RagBaseModel):
    gate_name: str
    threshold: float
    comparator: str
    metric_name: str
    required: bool = True


class RagQualityGateResult(RagBaseModel):
    gate_name: str
    metric_name: str
    observed_value: float
    threshold: float
    comparator: str
    passed: bool
    required: bool = True


class RagEvaluationManifest(RagBaseModel):
    rag_evaluation_id: str
    source_rag_run_id: str
    evaluated_query_count: int
    answer_status_accuracy: float
    retrieval_abstention_propagation_accuracy: float
    unsupported_clinical_request_refusal_rate: float
    real_patient_request_refusal_rate: float
    emergency_request_refusal_rate: float
    citation_presence_rate: float
    citation_validity_rate: float
    citation_correctness: float
    citation_completeness: float
    claim_support_precision: float
    claim_support_recall: float
    unsupported_claim_rate: float
    numeric_consistency_rate: float
    negation_consistency_rate: float
    required_fact_coverage: float
    prohibited_fact_violation_rate: float
    conflict_detection_accuracy: float
    grounded_answer_rate: float
    holdout_grounded_answer_rate: float
    error_count: int
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    approval_status: str
    approved_for_local_synthetic_demo: bool
    evaluation_reconciliation_status: str
    output_checksums: dict[str, str]


class RagApprovalDecision(RagBaseModel):
    rag_evaluation_id: str
    source_rag_run_id: str
    rag_configuration: str
    generator_provider: str
    approval_status: str
    approved_for_local_synthetic_demo: bool
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    known_failures: list[str]


class RagModelCard(RagBaseModel):
    system_name: str
    version: str
    system_type: str
    retrieval_baseline: str
    generator_type: str
    prompt_contracts: list[str]
    evaluation_metrics: dict[str, float]
    known_limitations: list[str]
    unsupported_uses: list[str]
    synthetic_only: bool
    clinically_validated: bool


class RagMLflowPlan(RagBaseModel):
    rag_run_id: str
    rag_evaluation_id: str
    retrieval_configuration_id: str
    prompt_versions: list[str]
    generator_provider: str
    generation_parameters: dict[str, Any]
    artifacts: list[str]
    dry_run_status: str
    connection_attempted: bool
    execution_permitted: bool


class RagDatabricksPlan(RagBaseModel):
    rag_run_id: str
    rag_evaluation_id: str
    logical_tables: list[str]
    target_state_workflows: list[str]
    dry_run_status: str
    connection_attempted: bool
    execution_permitted: bool
