"""Run deterministic local demonstration scenarios."""

from __future__ import annotations

import hashlib

from healthcare_language_ai.application.contracts import QueryRequest
from healthcare_language_ai.application.dependencies import ApplicationServices, build_services
from healthcare_language_ai.demonstration.contracts import DemoResult, DemoSession
from healthcare_language_ai.demonstration.scenarios import load_standard_scenarios


def run_demo_session(
    scenario_set: str = "standard", services: ApplicationServices | None = None
) -> DemoSession:
    if scenario_set != "standard":
        msg = "only the standard scenario set is available"
        raise ValueError(msg)
    resolved = services or build_services()
    results: list[DemoResult] = []
    for scenario in load_standard_scenarios():
        response = resolved.query.run_synthetic_query(
            QueryRequest(
                query_text=scenario.query_text,
                query_id=scenario.query_id,
                portfolio_demo_mode=True,
                include_trace=True,
            )
        )
        trace = resolved.trace.get_trace(response.answer_id)
        results.append(
            DemoResult(
                scenario_id=scenario.scenario_id,
                query_id=scenario.query_id,
                expected_status=scenario.expected_answer_status,
                actual_status=response.answer_status,
                retrieval_status=response.retrieval_status,
                answer_status=response.answer_status,
                citation_count=len(response.citations),
                groundedness_outcome=trace.groundedness_status,
                safety_outcome=trace.safety_status,
                passed=response.answer_status == scenario.expected_answer_status,
                answer_id=response.answer_id,
            )
        )
    seed = "|".join(result.scenario_id + result.answer_id for result in results)
    demo_session_id = "DEMO-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return DemoSession(
        demo_session_id=demo_session_id,
        scenario_set=scenario_set,
        scenario_count=len(results),
        passed_scenarios=sum(result.passed for result in results),
        failed_scenarios=sum(not result.passed for result in results),
        results=results,
    )
