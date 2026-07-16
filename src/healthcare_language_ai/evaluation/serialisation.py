"""Stable serialization for evaluation evidence."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from healthcare_language_ai.synthetic.serialization import write_json

ENTITY_METRIC_COLUMNS = [
    "metric_scope",
    "scope_value",
    "true_positive_count",
    "false_positive_count",
    "false_negative_count",
    "precision",
    "recall",
    "f1",
    "support",
    "evaluation_run_id",
]
CLASSIFICATION_METRIC_COLUMNS = [
    "class_label",
    "true_positive_count",
    "false_positive_count",
    "false_negative_count",
    "precision",
    "recall",
    "f1",
    "support",
    "accuracy",
    "evaluation_run_id",
]
CONFUSION_COLUMNS = [
    "actual_document_type",
    "predicted_document_type",
    "count",
    "evaluation_run_id",
]
MATCH_COLUMNS = [
    "match_id",
    "document_id",
    "label",
    "prediction_id",
    "ground_truth_annotation_id",
    "match_type",
    "matching_policy",
    "start_offset",
    "end_offset",
    "evaluation_run_id",
]
ERROR_COLUMNS = [
    "error_id",
    "document_id",
    "document_type",
    "label",
    "error_type",
    "prediction_id",
    "ground_truth_annotation_id",
    "predicted_value",
    "expected_value",
    "predicted_start",
    "predicted_end",
    "expected_start",
    "expected_end",
    "section_label",
    "sentence_id",
    "rule_id",
    "sanitised_context",
    "context_checksum",
    "likely_reason",
    "evaluation_run_id",
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


def write_json_model(path: Path, model: BaseModel | dict[str, Any]) -> None:
    write_json(path, model)
