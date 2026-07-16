"""Typed contracts shared by CLI, API, dashboard, and tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DISCLAIMER = (
    "Synthetic portfolio demonstration only. Not for patient care. "
    "Not medical advice. Not clinically validated."
)


class ApplicationBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CitationSummary(ApplicationBaseModel):
    citation_id: str
    citation_label: str
    evidence_id: str
    document_id: str
    section_id: str = ""
    sentence_id: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    citation_status: str
    quoted_span: str
    source_text_checksum: str


class QueryRequest(ApplicationBaseModel):
    query_text: str = Field(min_length=1)
    query_id: str | None = None
    metadata_filters: dict[str, str] = Field(default_factory=dict)
    portfolio_demo_mode: bool = True
    include_trace: bool = False


class QueryResponse(ApplicationBaseModel):
    request_id: str
    query_id: str
    answer_id: str
    answer_status: str
    answer_text: str
    citations: list[CitationSummary]
    retrieval_status: str
    retrieval_confidence: float
    trace_id: str
    synthetic_data_only: bool = True
    clinical_use_prohibited: bool = True
    disclaimer: str = DISCLAIMER


class AnswerResponse(QueryResponse):
    rag_run_id: str
    prompt_id: str
    prompt_version: str
    generator_provider: str
    generator_version: str


class EvidenceResponse(ApplicationBaseModel):
    evidence_id: str
    retrieval_unit_id: str
    document_id: str
    section_id: str = ""
    sentence_id: str = ""
    unit_type: str
    rank: int
    retrieval_score: float
    retrieval_confidence: float
    bounded_snippet: str
    text_checksum: str
    source_preprocessing_run_id: str
    source_extraction_run_id: str
    source_index_id: str


class CitationResponse(CitationSummary):
    bounded_text: str


class TraceResponse(ApplicationBaseModel):
    trace_id: str
    answer_id: str
    query_id: str
    query_category: str
    answer_status: str
    retrieval_status: str
    retrieval_configuration_id: str
    retrieval_approval_id: str
    retrieval_confidence: float
    selected_evidence_ids: list[str]
    excluded_retrieval_unit_ids: list[str]
    prompt_id: str
    prompt_version: str
    generator_provider: str
    generator_version: str
    claim_ids: list[str]
    citation_ids: list[str]
    citation_validation_status: str
    groundedness_status: str
    safety_status: str
    synthetic_data_only: bool = True
    clinical_use_prohibited: bool = True


class ApprovalResponse(ApplicationBaseModel):
    approval_type: Literal["retrieval", "rag"]
    approval_id: str
    approval_status: str
    approved_for_local_synthetic_demo: bool
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    configuration: str
    known_failures: list[str] = Field(default_factory=list)


class QualityGateResponse(ApplicationBaseModel):
    gate_set: Literal["retrieval", "rag"]
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    gates: list[dict[str, Any]]


class SystemStatusResponse(ApplicationBaseModel):
    application: str
    version: str
    application_service_version: str
    api_contract_version: str
    api_version: str
    streamlit_demo_version: str
    synthetic_data_only: bool
    clinical_use_prohibited: bool
    retrieval_approval_status: str
    rag_approval_status: str
    approved_retrieval_configuration: str
    generator_mode: str
    operational_events_enabled: bool


class HealthResponse(ApplicationBaseModel):
    status: Literal["ok"]
    application: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReadinessCheck(ApplicationBaseModel):
    name: str
    status: Literal["passed", "failed"]
    required: bool = True
    detail: str = ""


class ReadinessResponse(ApplicationBaseModel):
    status: Literal["ready", "not_ready"]
    readiness_version: str
    checks: list[ReadinessCheck]
    synthetic_data_only: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricSummaryResponse(ApplicationBaseModel):
    event_count: int
    request_count: int
    grounded_answer_count: int
    refusal_count: int
    retrieval_abstention_count: int
    citation_failure_count: int
    groundedness_failure_count: int
    safety_failure_count: int
    error_count: int
    p50_duration_ms: float
    p95_duration_ms: float


class ApiError(ApplicationBaseModel):
    error_code: str
    message: str
    request_id: str
    status: int
    details: dict[str, str] = Field(default_factory=dict)
