"""Stable preprocessing output serialization."""

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
    "source_text",
    "normalised_text",
    "analytical_text",
    "preprocessing_mode",
    "source_character_count",
    "normalised_character_count",
    "sentence_count",
    "section_count",
    "token_count",
    "unique_token_count",
    "line_count",
    "empty_line_count",
    "uppercase_ratio",
    "digit_ratio",
    "whitespace_ratio",
    "contains_replacement_character",
    "source_record_checksum",
    "normalised_text_checksum",
    "analytical_text_checksum",
    "ingestion_run_id",
    "preprocessing_run_id",
    "preprocessed_at",
    "normalisation_version",
    "section_parser_version",
    "sentence_segmenter_version",
    "tokeniser_version",
    "quality_rules_version",
]
SECTION_COLUMNS = [
    "section_id",
    "document_id",
    "section_index",
    "section_label",
    "normalised_section_label",
    "heading_start",
    "heading_end",
    "content_start",
    "content_end",
    "section_text",
    "section_text_checksum",
    "parser_rule",
    "preprocessing_run_id",
]
SENTENCE_COLUMNS = [
    "sentence_id",
    "document_id",
    "section_id",
    "sentence_index",
    "document_sentence_index",
    "start_offset",
    "end_offset",
    "sentence_text",
    "sentence_text_checksum",
    "token_count",
    "contains_negation_marker",
    "contains_numeric_value",
    "contains_synthetic_identifier",
    "boundary_rule",
    "preprocessing_run_id",
]
PROJECTION_COLUMNS = [
    "projection_id",
    "annotation_id",
    "document_id",
    "annotation_type",
    "label",
    "value",
    "source_start",
    "source_end",
    "target_start",
    "target_end",
    "projection_status",
    "projection_rule",
    "preprocessing_run_id",
]
QUALITY_COLUMNS = [
    "document_id",
    "check_name",
    "status",
    "severity",
    "observed_value",
    "threshold",
    "message",
    "preprocessing_run_id",
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


def write_parquet(
    path: Path, rows: Sequence[BaseModel], columns: list[str], *, compression: str
) -> None:
    table = pa.Table.from_pylist(rows_to_dicts(rows, columns))
    pq.write_table(table, path, compression=None if compression == "none" else compression)


def write_json_model(path: Path, model: BaseModel | dict[str, Any]) -> None:
    write_json(path, model)


def parquet_row_count(path: Path) -> int:
    return int(pq.read_table(path).num_rows)


def parquet_schema_names(path: Path) -> list[str]:
    return list(pq.read_table(path).schema.names)
