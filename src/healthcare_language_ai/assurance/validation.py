"""Validation helpers for generated assurance evidence."""

from __future__ import annotations

from pathlib import Path


def require_files(root: Path, names: list[str]) -> list[str]:
    return [name for name in names if not (root / name).exists()]
