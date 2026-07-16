from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app

runner = CliRunner()

PREPROCESSING_FIXTURE = "tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc"
EXTRACTION_FIXTURE = "tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d"
EVALUATION_FIXTURE = "tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605"


def test_extract_cli_run_validate_summary(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "extract-run",
            "--preprocessing-dir",
            PREPROCESSING_FIXTURE,
            "--output-root",
            str(tmp_path),
            "--text-representation",
            "normalised_text",
            "--reference-timestamp",
            "2026-01-04T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert result.exit_code == 0
    assert "Extraction completed" in result.output
    generated = tmp_path / "EXT-723871c87dfd1f3a3bb89b8d"
    validation = runner.invoke(app, ["extract-validate", "--extraction-dir", str(generated)])
    assert validation.exit_code == 0
    summary = runner.invoke(app, ["extract-summary", "--extraction-dir", str(generated)])
    assert summary.exit_code == 0
    assert "Entity prediction count: 66" in summary.output
    assert "This is a synthetic document" not in summary.output


def test_evaluate_cli_run_validate_summary_and_mlflow(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "evaluate-run",
            "--extraction-dir",
            EXTRACTION_FIXTURE,
            "--preprocessing-dir",
            PREPROCESSING_FIXTURE,
            "--output-root",
            str(tmp_path),
            "--matching-policy",
            "exact",
            "--reference-timestamp",
            "2026-01-05T09:00:00+00:00",
            "--overwrite-policy",
            "force_replace",
        ],
    )
    assert result.exit_code == 0
    generated = tmp_path / "EVAL-a56c0ad131cdbb85a69e1605"
    validation = runner.invoke(app, ["evaluate-validate", "--evaluation-dir", str(generated)])
    assert validation.exit_code == 0
    summary = runner.invoke(app, ["evaluate-summary", "--evaluation-dir", str(generated)])
    assert summary.exit_code == 0
    assert "Entity micro F1: 1.0" in summary.output
    plan = runner.invoke(app, ["mlflow-plan", "--evaluation-dir", str(generated)])
    assert plan.exit_code == 0
    assert "Connection attempted: false" in plan.output


def test_invalid_extraction_source_returns_non_zero() -> None:
    result = runner.invoke(
        app,
        [
            "extract-run",
            "--preprocessing-dir",
            "does-not-exist",
            "--output-root",
            "outputs/extraction",
        ],
    )
    assert result.exit_code == 1
