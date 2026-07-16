"""Identifier helpers for random and deterministic IDs."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def new_uuid(prefix: str | None = None) -> str:
    """Return a UUID4 identifier, optionally prefixed for readability."""
    value = str(uuid.uuid4())
    return f"{prefix}_{value}" if prefix else value


def _canonicalise(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def deterministic_id(value: Any, *, prefix: str | None = None, length: int = 32) -> str:
    """Return a stable hash-derived identifier for canonical input."""
    if length < 8 or length > 64:
        msg = "length must be between 8 and 64 characters"
        raise ValueError(msg)
    digest = hashlib.sha256(_canonicalise(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}" if prefix else digest
