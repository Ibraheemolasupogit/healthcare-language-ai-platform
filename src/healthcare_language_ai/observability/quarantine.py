"""Quarantine summary helpers."""

from pathlib import Path


def quarantine_summary(quarantine_root: Path) -> dict[str, int]:
    files = list(quarantine_root.glob("*.json")) if quarantine_root.exists() else []
    return {"quarantined_file_count": len(files)}
