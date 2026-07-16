"""Operational manifest helpers."""

from pathlib import Path

from healthcare_language_ai.observability.integrity import file_checksum


def checksum_manifest(paths: list[Path]) -> dict[str, str]:
    return {path.as_posix(): file_checksum(path) for path in sorted(paths)}
