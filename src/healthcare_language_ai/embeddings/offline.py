"""Offline safeguards for optional local embedding models."""

from __future__ import annotations

import os
from pathlib import Path

OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
}


def offline_environment() -> dict[str, str]:
    return {key: os.environ.get(key, value) for key, value in OFFLINE_ENVIRONMENT.items()}


def reject_remote_identifier(model_path: Path | str) -> Path:
    raw = str(model_path)
    if "://" in raw or ("/" in raw and not raw.startswith("/")):
        raise ValueError("local embedding model must be an explicit local filesystem path")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ValueError("local embedding model path must be absolute")
    return path
