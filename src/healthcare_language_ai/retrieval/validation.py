"""Validation for retrieval index, run and evaluation evidence."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from healthcare_language_ai.retrieval.contracts import (
    IndexManifest,
    RetrievalEvaluationManifest,
    RetrievalManifest,
)
from healthcare_language_ai.retrieval.corpus import checksum_text
from healthcare_language_ai.retrieval.serialisation import parquet_row_count
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_index_dir(index_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = IndexManifest.model_validate(read_json(index_dir / "index_manifest.json"))
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = index_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    rows = _csv_rows(index_dir / "retrieval_units.csv")
    unit_ids = [row["retrieval_unit_id"] for row in rows]
    if len(unit_ids) != len(set(unit_ids)):
        failures.append("retrieval unit IDs are not unique")
    if len(rows) != manifest.retrieval_unit_count:
        failures.append("retrieval unit count mismatch")
    if parquet_row_count(index_dir / "retrieval_units.parquet") != manifest.retrieval_unit_count:
        failures.append("retrieval unit Parquet count mismatch")
    for row in rows:
        if not row["text"]:
            failures.append(f"empty retrieval unit text: {row['retrieval_unit_id']}")
        if checksum_text(row["text"]) != row["text_checksum"]:
            failures.append(f"text checksum mismatch: {row['retrieval_unit_id']}")
    vocab = read_json(index_dir / "vocabulary.json")["vocabulary"]
    if len(vocab) != manifest.vocabulary_size:
        failures.append("vocabulary size mismatch")
    embeddings = read_json(index_dir / "hash_embeddings.json")
    for unit_id, vector in embeddings.items():
        if len(vector) != manifest.embedding_dimension:
            failures.append(f"embedding dimension mismatch: {unit_id}")
        if any(not math.isfinite(float(value)) for value in vector):
            failures.append(f"embedding contains non-finite value: {unit_id}")
    if manifest.reconciliation_status == "failed":
        failures.append("index reconciliation failed")
    return failures


def validate_retrieval_dir(retrieval_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = RetrievalManifest.model_validate(
        read_json(retrieval_dir / "retrieval_manifest.json")
    )
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = retrieval_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    rows = _csv_rows(retrieval_dir / "retrieval_results.csv")
    if len(rows) != manifest.returned_result_count:
        failures.append("retrieval result count mismatch")
    by_query: dict[str, list[int]] = {}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["query_id"], row["retrieval_unit_id"])
        if key in seen:
            failures.append(f"duplicate result for query: {row['query_id']}")
        seen.add(key)
        by_query.setdefault(row["query_id"], []).append(int(row["rank"]))
        if not math.isfinite(float(row["score"])):
            failures.append(f"non-finite score: {row['query_id']}")
    for query_id, ranks in by_query.items():
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            failures.append(f"non-contiguous ranks: {query_id}")
        if len(ranks) > manifest.top_k:
            failures.append(f"top-k exceeded: {query_id}")
    return failures


def validate_retrieval_evaluation_dir(evaluation_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = RetrievalEvaluationManifest.model_validate(
        read_json(evaluation_dir / "retrieval_evaluation_manifest.json")
    )
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = evaluation_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    plan = json.loads((evaluation_dir / "vector_search_plan.json").read_text(encoding="utf-8"))
    if plan["connection_attempted"] or plan["execution_permitted"]:
        failures.append("vector-search plan is not dry-run safe")
    mlflow = json.loads((evaluation_dir / "retrieval_mlflow_plan.json").read_text(encoding="utf-8"))
    if mlflow["connection_attempted"] or mlflow["execution_permitted"]:
        failures.append("retrieval MLflow plan is not dry-run safe")
    return failures
