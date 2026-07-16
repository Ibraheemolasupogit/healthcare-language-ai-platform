"""Operational metric service."""

from __future__ import annotations

from healthcare_language_ai.application.contracts import MetricSummaryResponse
from healthcare_language_ai.observability.contracts import OperationalEvent
from healthcare_language_ai.observability.metrics import aggregate_events, render_prometheus
from healthcare_language_ai.observability.store import EventStore


class MetricsService:
    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store

    def record(self, event: OperationalEvent) -> None:
        self.event_store.append(event)

    def summary(self) -> MetricSummaryResponse:
        return aggregate_events(self.event_store.read_events())

    def prometheus(self, readiness_status: str) -> str:
        return render_prometheus(self.summary(), readiness_status)
