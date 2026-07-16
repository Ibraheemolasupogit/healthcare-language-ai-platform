from __future__ import annotations

from pathlib import Path

import pytest

from healthcare_language_ai.config import AppSettings, load_settings
from healthcare_language_ai.exceptions import ConfigurationError, DataGovernanceError


def test_configuration_defaults() -> None:
    settings = AppSettings()
    assert settings.environment == "local"
    assert settings.synthetic_data_only is True
    assert settings.data_root == Path("data")


def test_yaml_configuration_loading(yaml_config: Path) -> None:
    settings = load_settings(yaml_config)
    assert settings.application_name == "Test Healthcare Language AI"
    assert settings.environment == "test"
    assert settings.max_document_text_length == 1234


def test_environment_variable_override(monkeypatch: pytest.MonkeyPatch, yaml_config: Path) -> None:
    monkeypatch.setenv("HEALTHCARE_LANGUAGE_AI_LOG_LEVEL", "ERROR")
    settings = load_settings(yaml_config)
    assert settings.log_level == "ERROR"


def test_malformed_configuration_failure(tmp_path: Path) -> None:
    malformed = tmp_path / "bad.yaml"
    malformed.write_text("application_name: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(malformed)


def test_missing_configuration_failure(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / "missing.yaml")


def test_synthetic_data_only_enforcement(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.yaml"
    path.write_text("synthetic_data_only: false\n", encoding="utf-8")
    with pytest.raises(DataGovernanceError):
        load_settings(path)
