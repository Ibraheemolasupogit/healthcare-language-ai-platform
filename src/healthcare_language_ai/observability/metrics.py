"""Metric aggregation and local Prometheus-compatible rendering."""

from __future__ import annotations

from statistics import median

from healthcare_language_ai.application.contracts import MetricSummaryResponse
from healthcare_language_ai.observability.contracts import OperationalEvent


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return float(ordered[index])


def aggregate_events(events: list[OperationalEvent]) -> MetricSummaryResponse:
    durations = [event.duration_ms for event in events if event.duration_ms >= 0]
    request_count = sum(
        event.event_type in {"query_accepted", "query_refused_before_retrieval"} for event in events
    )
    return MetricSummaryResponse(
        event_count=len(events),
        request_count=request_count,
        grounded_answer_count=sum(event.answer_status == "grounded_answer" for event in events),
        refusal_count=sum("refusal" in event.answer_status for event in events),
        retrieval_abstention_count=sum(
            event.retrieval_status == "retrieval_abstained" for event in events
        ),
        citation_failure_count=sum(event.citation_status == "failed" for event in events),
        groundedness_failure_count=sum(event.groundedness_status == "failed" for event in events),
        safety_failure_count=sum(event.safety_status == "failed" for event in events),
        error_count=sum(
            bool(event.error_code) or event.event_type == "application_error" for event in events
        ),
        p50_duration_ms=float(median(durations)) if durations else 0.0,
        p95_duration_ms=percentile(durations, 0.95),
    )


def render_prometheus(summary: MetricSummaryResponse, readiness_status: str) -> str:
    ready = "1" if readiness_status == "ready" else "0"
    lines = [
        f"hla_requests_total {summary.request_count}",
        f"hla_answers_total {summary.grounded_answer_count}",
        f"hla_refusals_total {summary.refusal_count}",
        f"hla_retrieval_abstentions_total {summary.retrieval_abstention_count}",
        f"hla_citation_failures_total {summary.citation_failure_count}",
        f"hla_groundedness_failures_total {summary.groundedness_failure_count}",
        f"hla_safety_failures_total {summary.safety_failure_count}",
        f'hla_request_duration_seconds{{quantile="0.5"}} {summary.p50_duration_ms / 1000:.6f}',
        f'hla_request_duration_seconds{{quantile="0.95"}} {summary.p95_duration_ms / 1000:.6f}',
        f"hla_readiness_status {ready}",
    ]
    return "\n".join(lines) + "\n"
