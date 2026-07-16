"""Safe operational event contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ObservabilityBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OperationalEvent(ObservabilityBaseModel):
    event_id: str
    event_type: str
    request_id: str
    query_checksum: str = ""
    query_category: str = ""
    retrieval_status: str = ""
    answer_status: str = ""
    citation_status: str = ""
    groundedness_status: str = ""
    safety_status: str = ""
    error_code: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    application_version: str = "0.1.0"
    environment: str = "local"
    operational_event_version: str = "1.0.0"


class RequestEvent(OperationalEvent):
    event_type: Literal["query_accepted", "query_refused_before_retrieval"]


class QueryEvent(OperationalEvent):
    event_type: Literal["answer_generated", "answer_promoted", "answer_rejected"]


class RetrievalEvent(OperationalEvent):
    event_type: Literal["retrieval_abstained"]


class RagAnswerEvent(OperationalEvent):
    event_type: Literal["answer_generated"]


class CitationValidationEvent(OperationalEvent):
    event_type: Literal["citation_validation_passed", "citation_validation_failed"]


class GroundednessEvent(OperationalEvent):
    event_type: Literal["groundedness_validation_passed", "groundedness_validation_failed"]


class SafetyEvent(OperationalEvent):
    event_type: Literal["safety_validation_passed", "safety_validation_failed"]


class ErrorEvent(OperationalEvent):
    event_type: Literal["application_error"]


class MetricSnapshot(ObservabilityBaseModel):
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


class ReadinessSnapshot(ObservabilityBaseModel):
    status: str
    passed_checks: int
    failed_checks: int


class OperationalSummary(MetricSnapshot):
    canonical_grounded_answers: int
    canonical_refusals: int
