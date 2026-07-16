from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

FIXTURE_RUN_ID = "PRE-72e9829c61769cea948faacc"


def test_cli_preprocess_run_validate_summary_and_plan(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "preprocess-run",
            "--ingestion-dir",
            "tests/fixtures/ingestion/ING-92a15c8f10047400ee895203",
            "--output-root",
            str(tmp_path),
            "--mode",
            "conservative",
            "--reference-timestamp",
            "2026-01-03T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert result.exit_code == 0
    preprocessing_dir = tmp_path / FIXTURE_RUN_ID
    assert preprocessing_dir.exists()
    validate = runner.invoke(
        app, ["preprocess-validate", "--preprocessing-dir", str(preprocessing_dir)]
    )
    assert validate.exit_code == 0
    summary = runner.invoke(
        app, ["preprocess-summary", "--preprocessing-dir", str(preprocessing_dir)]
    )
    assert summary.exit_code == 0
    assert "Reason for attendance" not in summary.output
    plan = runner.invoke(app, ["databricks-plan", "--preprocessing-dir", str(preprocessing_dir)])
    assert plan.exit_code == 0
    assert "Connection attempted: false" in plan.output


def test_cli_invalid_preprocessing_source_returns_non_zero(
    runner: CliRunner, tmp_path: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "preprocess-run",
            "--ingestion-dir",
            str(tmp_path / "missing"),
            "--output-root",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code != 0
