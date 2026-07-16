from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from healthcare_language_ai.cli import app


def test_cli_generate_and_validate_succeed(runner: CliRunner, tmp_path: Path) -> None:
    dataset_dir = tmp_path / "synthetic"
    generate = runner.invoke(
        app,
        [
            "synthetic-generate",
            "--count",
            "5",
            "--seed",
            "2026",
            "--document-type",
            "all",
            "--reference-timestamp",
            "2026-01-01T09:00:00+00:00",
            "--output-dir",
            str(dataset_dir),
        ],
    )
    assert generate.exit_code == 0
    assert "Synthetic generation completed" in generate.output

    validate = runner.invoke(app, ["synthetic-validate", "--dataset-dir", str(dataset_dir)])
    assert validate.exit_code == 0
    assert "Validation status: passed" in validate.output


def test_cli_validate_returns_non_zero_for_invalid_data(runner: CliRunner, tmp_path: Path) -> None:
    dataset_dir = tmp_path / "missing"
    result = runner.invoke(app, ["synthetic-validate", "--dataset-dir", str(dataset_dir)])
    assert result.exit_code != 0


def test_cli_summary_does_not_print_full_document_text(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["synthetic-summary", "--dataset-dir", "tests/fixtures/synthetic"],
    )
    assert result.exit_code == 0
    assert "Record count: 15" in result.output
    assert "Reason for attendance" not in result.output
    assert "This is a synthetic document" not in result.output


def test_cli_unsupported_document_type_fails(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "synthetic-generate",
            "--count",
            "1",
            "--document-type",
            "operative_note",
            "--output-dir",
            str(tmp_path / "synthetic"),
        ],
    )
    assert result.exit_code != 0
    assert "unsupported document type" in result.output


def test_cli_maximum_record_limit_is_enforced(
    runner: CliRunner, tmp_path: Path, yaml_config: Path
) -> None:
    yaml_config.write_text(
        "\n".join(
            [
                "synthetic_generation:",
                "  maximum_records_per_run: 2",
                "  allowed_document_types: [clinical_note]",
            ]
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "synthetic-generate",
            "--count",
            "3",
            "--config",
            str(yaml_config),
            "--output-dir",
            str(tmp_path / "synthetic"),
        ],
    )
    assert result.exit_code != 0
    assert "maximum_records_per_run" in result.output
