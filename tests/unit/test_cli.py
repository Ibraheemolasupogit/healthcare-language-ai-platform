from __future__ import annotations

from typer.testing import CliRunner

from healthcare_language_ai.cli import app


def test_version_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Healthcare Language AI Platform" in result.output
    assert "0.1.0" in result.output


def test_cli_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "config-show" in result.output
    assert "validate-environment" in result.output


def test_config_show_uses_yaml(runner: CliRunner, yaml_config) -> None:  # type: ignore[no-untyped-def]
    result = runner.invoke(app, ["config-show", "--config", str(yaml_config)])
    assert result.exit_code == 0
    assert '"environment": "test"' in result.output
    assert '"synthetic_data_only": true' in result.output


def test_validate_environment_creates_paths(runner: CliRunner, yaml_config) -> None:  # type: ignore[no-untyped-def]
    result = runner.invoke(app, ["validate-environment", "--config", str(yaml_config)])
    assert result.exit_code == 0
    assert "Environment validation passed" in result.output
