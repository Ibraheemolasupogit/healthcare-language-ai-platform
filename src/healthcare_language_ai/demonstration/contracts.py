"""Contracts for deterministic demo sessions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DemoBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoScenario(DemoBaseModel):
    scenario_id: str
    name: str
    query_id: str
    query_text: str
    expected_answer_status: str


class DemoResult(DemoBaseModel):
    scenario_id: str
    query_id: str
    expected_status: str
    actual_status: str
    retrieval_status: str
    answer_status: str
    citation_count: int
    groundedness_outcome: str
    safety_outcome: str
    passed: bool
    answer_id: str


class DemoSession(DemoBaseModel):
    demo_session_id: str
    demo_session_version: str = "1.0.0"
    scenario_set: str
    scenario_count: int
    passed_scenarios: int
    failed_scenarios: int
    results: list[DemoResult] = Field(default_factory=list)
