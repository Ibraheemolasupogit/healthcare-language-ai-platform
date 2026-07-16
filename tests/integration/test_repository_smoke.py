from __future__ import annotations

from pathlib import Path

from healthcare_language_ai import __version__
from healthcare_language_ai.config import AppSettings, validate_local_environment


def test_package_import() -> None:
    assert __version__


def test_repository_smoke_paths_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = [
        root / "README.md",
        root / "pyproject.toml",
        root / "config" / "application.yaml",
        root / "docs" / "architecture.md",
        root / "src" / "healthcare_language_ai" / "cli.py",
    ]
    assert all(path.exists() for path in expected)


def test_validate_local_environment_with_temp_paths(tmp_path: Path) -> None:
    settings = AppSettings(
        data_root=tmp_path / "data",
        output_root=tmp_path / "outputs",
        report_root=tmp_path / "reports",
    )
    paths = validate_local_environment(settings)
    assert all(path.exists() for path in paths)
