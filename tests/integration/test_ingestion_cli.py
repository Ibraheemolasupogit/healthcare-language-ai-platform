from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

FIXTURE_RUN_ID = "ING-92a15c8f10047400ee895203"


def test_cli_ingest_run_validate_summary_and_plan(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "ingest-run",
            "--source-dir",
            "tests/fixtures/synthetic",
            "--output-root",
            str(tmp_path),
            "--mode",
            "strict",
            "--reference-timestamp",
            "2026-01-02T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert result.exit_code == 0
    ingestion_dir = tmp_path / FIXTURE_RUN_ID
    assert ingestion_dir.exists()
    validate = runner.invoke(app, ["ingest-validate", "--ingestion-dir", str(ingestion_dir)])
    assert validate.exit_code == 0
    summary = runner.invoke(app, ["ingest-summary", "--ingestion-dir", str(ingestion_dir)])
    assert summary.exit_code == 0
    assert "Reason for attendance" not in summary.output
    plan = runner.invoke(app, ["snowflake-plan", "--ingestion-dir", str(ingestion_dir)])
    assert plan.exit_code == 0
    assert "No Snowflake connection will be attempted." in plan.output


def test_cli_invalid_source_returns_non_zero(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "ingest-run",
            "--source-dir",
            str(tmp_path / "missing"),
            "--output-root",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code != 0
