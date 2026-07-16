"""Construction helpers for shared Milestone 10 services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from healthcare_language_ai.application.approval_service import ApprovalService
from healthcare_language_ai.application.evidence_service import EvidenceService
from healthcare_language_ai.application.health_service import HealthService
from healthcare_language_ai.application.metrics_service import MetricsService
from healthcare_language_ai.application.query_service import QueryService
from healthcare_language_ai.application.trace_service import TraceService
from healthcare_language_ai.config import AppSettings, load_settings
from healthcare_language_ai.observability.store import EventStore

DEFAULT_RAG_RUN_DIR = Path("tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874")
DEFAULT_RAG_EVALUATION_DIR = Path("tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017")
DEFAULT_RAG_QUERY_DIR = Path("tests/fixtures/rag/queries")
DEFAULT_RETRIEVAL_APPROVAL_DIR = Path(
    "tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352"
)


@dataclass(frozen=True)
class ApplicationServices:
    settings: AppSettings
    approval: ApprovalService
    evidence: EvidenceService
    trace: TraceService
    metrics: MetricsService
    health: HealthService
    query: QueryService


def build_services(settings: AppSettings | None = None) -> ApplicationServices:
    resolved = settings or load_settings()
    event_store = EventStore(
        root=resolved.milestone10.operational_event_root,
        max_bytes=resolved.milestone10.operational_event_max_bytes,
        retention_files=resolved.milestone10.operational_event_retention_files,
        enabled=resolved.milestone10.operational_events_enabled,
    )
    approval = ApprovalService(DEFAULT_RETRIEVAL_APPROVAL_DIR, DEFAULT_RAG_EVALUATION_DIR)
    evidence = EvidenceService(DEFAULT_RAG_RUN_DIR, DEFAULT_RAG_QUERY_DIR)
    metrics = MetricsService(event_store)
    trace = TraceService(evidence)
    health = HealthService(resolved, approval, evidence)
    query = QueryService(resolved, evidence, trace, metrics)
    return ApplicationServices(
        settings=resolved,
        approval=approval,
        evidence=evidence,
        trace=trace,
        metrics=metrics,
        health=health,
        query=query,
    )
