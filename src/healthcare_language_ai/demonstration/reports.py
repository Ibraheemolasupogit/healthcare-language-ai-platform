"""Write deterministic demonstration and portfolio reports."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from healthcare_language_ai.application.dependencies import build_services
from healthcare_language_ai.demonstration.contracts import DemoSession


def write_demo_report(session: DemoSession, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-session.json").write_text(
        session.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    with (output_dir / "demo-results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "scenario_id",
                "query_id",
                "expected_status",
                "actual_status",
                "retrieval_status",
                "answer_status",
                "citation_count",
                "groundedness_outcome",
                "safety_outcome",
                "passed",
                "answer_id",
            ],
        )
        writer.writeheader()
        for result in session.results:
            writer.writerow(result.model_dump())
    lines = [
        "# Demo Session Summary",
        "",
        f"Session ID: {session.demo_session_id}",
        f"Scenario count: {session.scenario_count}",
        f"Passed scenarios: {session.passed_scenarios}",
        f"Failed scenarios: {session.failed_scenarios}",
        "",
        "Synthetic portfolio demonstration only. No clinical text is included.",
    ]
    (output_dir / "demo-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    trace_index = {
        result.answer_id: {"query_id": result.query_id, "scenario_id": result.scenario_id}
        for result in session.results
    }
    (output_dir / "demo-trace-index.json").write_text(
        json.dumps(trace_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# Demo Fixture\n\nDeterministic fixture-backed local portfolio demonstration report.\n",
        encoding="utf-8",
    )
    return output_dir


def write_portfolio_summary(output_dir: Path) -> Path:
    services = build_services()
    output_dir.mkdir(parents=True, exist_ok=True)
    system = services.health.system_status()
    rag = services.evidence.manifest
    retrieval = services.approval.retrieval_approval()
    lines = [
        "# Platform Evidence Summary",
        "",
        "portfolio_summary_version: 1.0.0",
        "",
        "## Milestones completed",
        "Milestones 1 through 10 are represented by local synthetic evidence.",
        "",
        "## Capabilities implemented",
        "Shared application service layer, local read-only FastAPI API, Streamlit "
        "dashboard, operational events, demo runner, portfolio summary.",
        "",
        "## Approved retrieval baseline",
        f"Configuration: {retrieval.configuration}",
        f"Approval status: {retrieval.approval_status}",
        "",
        "## Approved RAG prototype",
        f"RAG run: {rag.rag_run_id}",
        f"Generator: {rag.generator_provider}",
        f"Grounded answers: {rag.grounded_answer_count}",
        f"Refusals: {rag.refusal_count}",
        "",
        "## Safety controls",
        "Synthetic-only data, bounded citations, query safety refusal, no hosted "
        "model calls, local-only observability.",
        "",
        "## Architecture boundaries",
        f"API version: {system.api_version}",
        "Cloud systems, production authentication, and clinical workflows are target-state only.",
        "",
        "## Target roles",
        "Healthcare AI engineer, NLP engineer, data platform engineer, applied ML "
        "governance engineer.",
        "",
        "## Interview talking points",
        "Deterministic fixtures, approval gates, RAG traceability, abstention "
        "propagation, local observability.",
        "",
        "## Known limitations",
        "No real patient data, no clinical validation, no hosted LLM, no production deployment.",
    ]
    path = output_dir / "platform-evidence-summary.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
