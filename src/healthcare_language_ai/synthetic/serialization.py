"""Stable serialization helpers for canonical dataset files."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def to_plain_json(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def canonical_json_line(value: BaseModel | dict[str, Any]) -> str:
    return json.dumps(
        to_plain_json(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def write_jsonl(path: Path, rows: Sequence[BaseModel | dict[str, Any]]) -> None:
    path.write_text(
        "".join(f"{canonical_json_line(row)}\n" for row in rows), encoding="utf-8", newline="\n"
    )


def write_json(path: Path, value: BaseModel | dict[str, Any]) -> None:
    path.write_text(f"{canonical_json_line(value)}\n", encoding="utf-8", newline="\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def read_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        msg = f"Expected JSON object in {path}"
        raise ValueError(msg)
    return loaded
