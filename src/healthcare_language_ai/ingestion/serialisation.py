"""Stable CSV, Parquet, and JSON serialization for ingestion outputs."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from healthcare_language_ai.synthetic.serialization import write_json

DOCUMENT_COLUMNS = [
    "document_id",
    "synthetic_subject_id",
    "synthetic_encounter_id",
    "document_type",
    "source_system",
    "data_classification",
    "document_text",
    "document_created_at",
    "encounter_started_at",
    "encounter_ended_at",
    "generator_version",
    "template_name",
    "template_version",
    "vocabulary_version",
    "source_dataset_name",
    "source_dataset_version",
    "source_seed",
    "source_reference_timestamp",
    "source_record_index",
    "source_file",
    "source_line_number",
    "source_record_checksum",
    "ingestion_run_id",
    "ingested_at",
]

ANNOTATION_COLUMNS = [
    "annotation_id",
    "document_id",
    "annotation_type",
    "label",
    "value",
    "normalised_value",
    "start_offset",
    "end_offset",
    "annotation_source",
    "source_annotation_index",
    "source_record_checksum",
    "ingestion_run_id",
]


def rows_to_dicts(rows: Sequence[BaseModel], columns: list[str]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        raw = row.model_dump(mode="json")
        payload.append({column: raw.get(column) for column in columns})
    return payload


def write_csv(
    path: Path, rows: Sequence[BaseModel], columns: list[str], *, null_value: str
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows_to_dicts(rows, columns):
            writer.writerow(
                {key: null_value if value is None else value for key, value in row.items()}
            )


def write_parquet(
    path: Path,
    rows: Sequence[BaseModel],
    columns: list[str],
    *,
    compression: str,
) -> None:
    data = rows_to_dicts(rows, columns)
    table = pa.Table.from_pylist(data)
    pq.write_table(table, path, compression=None if compression == "none" else compression)


def write_json_model(path: Path, model: BaseModel | dict[str, Any]) -> None:
    write_json(path, model)


def parquet_row_count(path: Path) -> int:
    return int(pq.read_table(path).num_rows)


def parquet_schema_names(path: Path) -> list[str]:
    return list(pq.read_table(path).schema.names)
