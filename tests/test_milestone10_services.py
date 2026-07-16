from pathlib import Path

from healthcare_language_ai.application.contracts import DISCLAIMER, QueryRequest
from healthcare_language_ai.application.dependencies import build_services
from healthcare_language_ai.demonstration.runner import run_demo_session
from healthcare_language_ai.observability.events import make_event
from healthcare_language_ai.observability.metrics import aggregate_events, render_prometheus
from healthcare_language_ai.observability.store import EventStore
from healthcare_language_ai.observability.validation import validate_event_dir


def test_shared_query_service_uses_canonical_fixture_and_trace() -> None:
    services = build_services()
    query = services.evidence.queries[0]
    response = services.query.run_synthetic_query(
        QueryRequest(query_text=query["query_text"], query_id=query["query_id"])
    )
    trace = services.trace.get_trace(response.answer_id)
    assert (
        response.answer_status
        == services.evidence.answer_by_query_id[query["query_id"]].answer_status
    )
    assert trace.query_id == response.query_id
    assert trace.selected_evidence_ids


def test_operational_events_are_sanitized_and_metrics_aggregate(tmp_path: Path) -> None:
    store = EventStore(tmp_path, max_bytes=1024, retention_files=2)
    event = make_event(
        event_type="query_accepted",
        request_id="REQ-test",
        query_text="Synthetic fixture query text that must not be stored",
        query_category="single_evidence",
        retrieval_status="evidence_selected",
        answer_status="grounded_answer",
        duration_ms=10.0,
    )
    store.append(event)
    raw = (tmp_path / "operational-events.jsonl").read_text()
    assert "Synthetic fixture query text" not in raw
    assert raw.endswith("\n")
    assert validate_event_dir(tmp_path) == []
    summary = aggregate_events(store.read_events())
    assert summary.event_count == 1
    assert summary.grounded_answer_count == 1
    prometheus = render_prometheus(summary, "ready")
    assert "document_id" not in prometheus
    assert "evidence_id" not in prometheus


def test_controlled_observability_fixture_validates() -> None:
    assert validate_event_dir(Path("tests/fixtures/observability")) == []


def test_demo_session_uses_shared_service_and_passes() -> None:
    session = run_demo_session("standard", services=build_services())
    assert session.scenario_count == 11
    assert session.failed_scenarios == 0
    assert all(result.answer_id.startswith("ANS-") for result in session.results)


def test_dashboard_guard_helper_and_banner_text() -> None:
    from dashboard.components.common import acknowledgement_required, safety_banner_text

    assert safety_banner_text() == DISCLAIMER
    assert not acknowledgement_required(False)
    assert acknowledgement_required(True)
