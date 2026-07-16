"""Optional offline local-generator guardrails."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.embeddings.model_metadata import directory_checksum


def reject_remote_identifier(model_path: str) -> None:
    if "://" in model_path or ("/" in model_path and not model_path.startswith("/")):
        raise ValueError("local generator requires an explicit local filesystem path")


def inspect_local_generator(model_path: Path) -> dict[str, str | bool]:
    reject_remote_identifier(str(model_path))
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    return {
        "model_path": str(model_path),
        "model_checksum": directory_checksum(model_path) if model_path.is_dir() else "",
        "automatic_download_attempted": False,
        "network_connection_attempted": False,
    }
