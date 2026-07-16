"""Stable serialization helpers for retrieval evidence."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from healthcare_language_ai.synthetic.serialization import write_json

UNIT_COLUMNS = [
    "retrieval_unit_id",
    "document_id",
    "section_id",
    "sentence_id",
    "unit_type",
    "document_type",
    "section_label",
    "text",
    "text_checksum",
    "token_count",
    "synthetic_subject_id",
    "synthetic_encounter_id",
    "source_preprocessing_run_id",
    "source_extraction_run_id",
    "corpus_version",
]
RESULT_COLUMNS = [
    "retrieval_run_id",
    "query_id",
    "rank",
    "retrieval_unit_id",
    "document_id",
    "section_id",
    "sentence_id",
    "unit_type",
    "document_type",
    "section_label",
    "score",
    "keyword_score",
    "tfidf_score",
    "bm25_score",
    "dense_score",
    "metadata_score",
    "fusion_score",
    "matched_terms",
    "text_checksum",
    "sanitised_snippet",
    "relevant",
    "relevance_grade",
]
METRIC_COLUMNS = [
    "metric_scope",
    "scope_value",
    "k",
    "query_count",
    "precision_at_k",
    "recall_at_k",
    "hit_rate_at_k",
    "mrr",
    "map_score",
    "ndcg_at_k",
    "zero_hit_query_count",
    "average_relevant_rank",
    "retrieval_evaluation_run_id",
]
FAILURE_COLUMNS = [
    "failure_id",
    "query_id",
    "query_category",
    "strategy",
    "failure_type",
    "expected_unit_id",
    "returned_unit_id",
    "expected_rank",
    "actual_rank",
    "relevant_score",
    "top_result_score",
    "matched_terms",
    "sanitised_query",
    "sanitised_result_snippet",
    "likely_reason",
    "retrieval_evaluation_run_id",
]


def rows_to_dicts(rows: Sequence[BaseModel], columns: list[str]) -> list[dict[str, Any]]:
    return [{column: row.model_dump(mode="json").get(column) for column in columns} for row in rows]


def write_csv(path: Path, rows: Sequence[BaseModel], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows_to_dicts(rows, columns):
            writer.writerow({key: "" if value is None else value for key, value in row.items()})


def write_parquet(path: Path, rows: Sequence[BaseModel], columns: list[str]) -> None:
    pq.write_table(pa.Table.from_pylist(rows_to_dicts(rows, columns)), path, compression="zstd")


def write_json_model(path: Path, model: BaseModel | dict[str, Any]) -> None:
    write_json(path, model)


def write_jsonl(path: Path, rows: Sequence[BaseModel]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(row.model_dump_json(exclude_none=False))
            stream.write("\n")


def parquet_row_count(path: Path) -> int:
    return int(pq.read_table(path).num_rows)
