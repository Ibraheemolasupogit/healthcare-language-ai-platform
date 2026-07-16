"""Stable serialization for extraction evidence."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from healthcare_language_ai.synthetic.serialization import write_json

ENTITY_COLUMNS = [
    "prediction_id",
    "document_id",
    "label",
    "value",
    "normalised_value",
    "start_offset",
    "end_offset",
    "prediction_scope",
    "confidence",
    "rule_id",
    "rule_version",
    "vocabulary_version",
    "matched_text",
    "source_text_representation",
    "section_id",
    "sentence_id",
    "preprocessing_run_id",
    "extraction_run_id",
]
DOCUMENT_CLASSIFICATION_COLUMNS = [
    "document_id",
    "predicted_document_type",
    "confidence",
    "matched_rule_ids",
    "score_by_class",
    "classification_rule_version",
    "extraction_run_id",
]
SECTION_CLASSIFICATION_COLUMNS = [
    "section_id",
    "document_id",
    "predicted_section_label",
    "confidence",
    "classification_rule_version",
    "extraction_run_id",
]


def rows_to_dicts(rows: Sequence[BaseModel], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row.model_dump(mode="json").get(column) for column in columns} for row in rows]


def write_csv(
    path: Path, rows: Sequence[BaseModel], columns: list[str], *, null_value: str = ""
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows_to_dicts(rows, columns):
            writer.writerow(
                {key: null_value if value is None else value for key, value in row.items()}
            )


def write_jsonl(path: Path, rows: Sequence[BaseModel]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(row.model_dump_json(by_alias=False, exclude_none=False))
            stream.write("\n")


def write_parquet(
    path: Path, rows: Sequence[BaseModel], columns: list[str], *, compression: str
) -> None:
    table = pa.Table.from_pylist(rows_to_dicts(rows, columns))
    pq.write_table(table, path, compression=None if compression == "none" else compression)


def write_json_model(path: Path, model: BaseModel | dict[str, Any]) -> None:
    write_json(path, model)


def parquet_row_count(path: Path) -> int:
    return int(pq.read_table(path).num_rows)
