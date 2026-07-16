"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def yaml_config(tmp_path: Path) -> Path:
    path = tmp_path / "application.yaml"
    path.write_text(
        "\n".join(
            [
                "application_name: Test Healthcare Language AI",
                "environment: test",
                "log_level: WARNING",
                "log_format: json",
                f"data_root: {tmp_path / 'data'}",
                f"output_root: {tmp_path / 'outputs'}",
                f"report_root: {tmp_path / 'reports'}",
                "synthetic_data_only: true",
                "max_document_text_length: 1234",
                "deterministic_seed: 99",
            ]
        ),
        encoding="utf-8",
    )
    return path
