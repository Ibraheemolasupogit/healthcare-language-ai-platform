"""RAG file serialisation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from healthcare_language_ai.retrieval_quality.io import (
    output_checksums,
    read_jsonl,
    write_csv,
    write_json,
    write_jsonl,
)


def dump_model_rows(rows: list[BaseModel]) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


__all__ = [
    "dump_model_rows",
    "output_checksums",
    "read_jsonl",
    "write_csv",
    "write_json",
    "write_jsonl",
]
