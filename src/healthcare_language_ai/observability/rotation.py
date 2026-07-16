"""Rotation validation helpers for local event stores."""

from pathlib import Path


def retained_jsonl_files(root: Path) -> list[Path]:
    return sorted(root.glob("*.jsonl"))
