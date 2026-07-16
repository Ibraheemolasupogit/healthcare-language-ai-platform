from fastapi.testclient import TestClient

from healthcare_language_ai.api.app import create_app
from healthcare_language_ai.application.dependencies import build_services


def test_fastapi_routes_openapi_and_security_headers() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json").json()
    assert "Synthetic-only" in openapi["info"]["description"]
    paths = set(openapi["paths"])
    assert "/api/v1/query" in paths
    assert not any(path.startswith("/api/v1/admin") for path in paths)

    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "access-control-allow-origin" not in response.headers


def test_readiness_system_and_lookup_endpoints_are_safe() -> None:
    client = TestClient(create_app())
    assert client.get("/health/ready").json()["status"] == "ready"
    system = client.get("/api/v1/system").json()
    assert "credential" not in str(system).lower()
    assert "/Users/" not in str(system)

    services = build_services()
    answer = services.evidence.answers[0]
    citation = answer.citations[0]
    evidence_id = citation.evidence_id
    assert client.get(f"/api/v1/answers/{answer.answer_id}").json()["answer_id"] == answer.answer_id
    trace = client.get(f"/api/v1/traces/{answer.answer_id}").json()
    assert trace["selected_evidence_ids"]
    assert "text" not in trace
    assert len(client.get(f"/api/v1/evidence/{evidence_id}").json()["bounded_snippet"]) <= 240
    assert (
        len(client.get(f"/api/v1/citations/{citation.citation_id}").json()["bounded_text"]) <= 160
    )
    assert client.get("/api/v1/answers/unknown").status_code == 404
    assert "traceback" not in client.get("/api/v1/answers/unknown").text.lower()


def test_query_contract_success_limits_and_refusals() -> None:
    client = TestClient(create_app())
    services = build_services()
    query = services.evidence.queries[0]
    response = client.post(
        "/api/v1/query",
        json={
            "query_text": query["query_text"],
            "query_id": query["query_id"],
            "portfolio_demo_mode": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert (
        body["answer_status"]
        == services.evidence.answer_by_query_id[query["query_id"]].answer_status
    )
    assert body["citations"]

    oversized = client.post("/api/v1/query", json={"query_text": "x" * 501})
    assert oversized.status_code == 400
    assert oversized.json()["error_code"] == "query_too_large"

    for text in [
        "Give clinical advice",
        "diagnose this condition",
        "what treatment should I use",
        "what medication dosage",
        "my patient has symptoms",
        "this is an emergency",
    ]:
        refused = client.post(
            "/api/v1/query", json={"query_text": text, "portfolio_demo_mode": True}
        )
        assert refused.status_code == 200
        assert "refusal" in refused.json()["answer_status"]


def test_api_and_service_resolve_same_answer_status() -> None:
    services = build_services()
    client = TestClient(create_app())
    answer = services.evidence.answers[0]
    api_answer = client.get(f"/api/v1/answers/{answer.answer_id}").json()
    service_answer = services.evidence.answer_response(answer.answer_id)
    assert api_answer["answer_status"] == service_answer.answer_status
    assert api_answer["answer_id"] == service_answer.answer_id
