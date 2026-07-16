"""Fixture-backed local demonstration scenarios."""

from __future__ import annotations

from healthcare_language_ai.application.dependencies import build_services
from healthcare_language_ai.demonstration.contracts import DemoScenario

STANDARD_SCENARIO_COUNT = 11


def load_standard_scenarios() -> list[DemoScenario]:
    services = build_services()
    selected: list[DemoScenario] = []
    wanted = [
        "grounded_answer",
        "conflicting_evidence",
        "unanswerable_refusal",
        "unsupported_request_refusal",
    ]
    for status in wanted:
        for answer in services.evidence.answers:
            if answer.answer_status == status and answer.query_id not in {
                item.query_id for item in selected
            }:
                query = services.evidence.query_by_id[answer.query_id]
                selected.append(
                    DemoScenario(
                        scenario_id=f"scenario-{len(selected) + 1:02d}",
                        name=status.replace("_", " "),
                        query_id=answer.query_id,
                        query_text=str(query["query_text"]),
                        expected_answer_status=answer.answer_status,
                    )
                )
                break
    for answer in services.evidence.answers:
        if len(selected) >= STANDARD_SCENARIO_COUNT:
            break
        if answer.query_id in {item.query_id for item in selected}:
            continue
        query = services.evidence.query_by_id[answer.query_id]
        selected.append(
            DemoScenario(
                scenario_id=f"scenario-{len(selected) + 1:02d}",
                name=str(query.get("query_category", "fixture query")).replace("_", " "),
                query_id=answer.query_id,
                query_text=str(query["query_text"]),
                expected_answer_status=answer.answer_status,
            )
        )
    return selected
