from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

COMPARISON = "tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352"


def test_rag_cli_end_to_end(runner: CliRunner, tmp_path: Path) -> None:
    query_dir = tmp_path / "queries"
    query_result = runner.invoke(app, ["rag-query-fixtures", "--output-dir", str(query_dir)])
    assert query_result.exit_code == 0
    assert "Query count: 55" in query_result.output

    run_root = tmp_path / "runs"
    run_result = runner.invoke(
        app,
        [
            "rag-run",
            "--query-set",
            str(query_dir / "rag_queries.jsonl"),
            "--retrieval-comparison-dir",
            COMPARISON,
            "--output-root",
            str(run_root),
            "--generator",
            "deterministic_extract",
            "--reference-timestamp",
            "2026-01-16T09:00:00+00:00",
        ],
    )
    assert run_result.exit_code == 0
    rag_dir = next(run_root.iterdir())
    assert runner.invoke(app, ["rag-validate", "--rag-dir", str(rag_dir)]).exit_code == 0
    assert runner.invoke(app, ["rag-summary", "--rag-dir", str(rag_dir)]).exit_code == 0

    eval_root = tmp_path / "evaluation"
    eval_result = runner.invoke(
        app,
        [
            "rag-evaluate",
            "--rag-dir",
            str(rag_dir),
            "--expected-outcomes",
            str(query_dir / "rag_expected_outcomes.jsonl"),
            "--output-root",
            str(eval_root),
            "--reference-timestamp",
            "2026-01-17T09:00:00+00:00",
        ],
    )
    assert eval_result.exit_code == 0
    evaluation_dir = next(eval_root.iterdir())
    assert (
        runner.invoke(
            app, ["rag-evaluate-validate", "--evaluation-dir", str(evaluation_dir)]
        ).exit_code
        == 0
    )
    approval = runner.invoke(app, ["rag-approval", "--evaluation-dir", str(evaluation_dir)])
    assert approval.exit_code == 0
    assert "Approved for local synthetic demo: true" in approval.output
    assert (
        runner.invoke(app, ["rag-mlflow-plan", "--evaluation-dir", str(evaluation_dir)]).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["rag-databricks-plan", "--evaluation-dir", str(evaluation_dir)]
        ).exit_code
        == 0
    )

    first_answer = (rag_dir / "rag_answers.jsonl").read_text().splitlines()[0]
    import json

    query_id = json.loads(first_answer)["query_id"]
    trace = runner.invoke(app, ["rag-trace", "--rag-dir", str(rag_dir), "--query-id", query_id])
    assert trace.exit_code == 0
    assert "Answer status:" in trace.output
