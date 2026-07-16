"""Validation for persisted preprocessing evidence."""

from __future__ import annotations

import csv
from pathlib import Path

from healthcare_language_ai.preprocessing.contracts import (
    DatabricksPipelinePlan,
    PreprocessingManifest,
    PreprocessingReconciliationReport,
)
from healthcare_language_ai.preprocessing.databricks import validate_table_contracts
from healthcare_language_ai.preprocessing.serialisation import parquet_row_count
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json


def _csv_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def validate_preprocessing_dir(preprocessing_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = PreprocessingManifest.model_validate(
        read_json(preprocessing_dir / "preprocessing_manifest.json")
    )
    reconciliation = PreprocessingReconciliationReport.model_validate(
        read_json(preprocessing_dir / "preprocessing_reconciliation.json")
    )
    plan = DatabricksPipelinePlan.model_validate(
        read_json(preprocessing_dir / "databricks_pipeline_plan.json")
    )
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = preprocessing_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    checks = {
        "processed_documents": manifest.processed_document_count,
        "processed_sections": manifest.section_count,
        "processed_sentences": manifest.sentence_count,
        "projected_annotations": manifest.projected_annotation_count
        + manifest.unresolved_annotation_count,
    }
    for stem, expected_count in checks.items():
        csv_path = preprocessing_dir / f"{stem}.csv"
        parquet_path = preprocessing_dir / f"{stem}.parquet"
        if csv_path.exists() and _csv_count(csv_path) != expected_count:
            failures.append(f"CSV row count mismatch: {stem}")
        if parquet_path.exists() and parquet_row_count(parquet_path) != expected_count:
            failures.append(f"Parquet row count mismatch: {stem}")
    if reconciliation.overall_status != manifest.reconciliation_status:
        failures.append("reconciliation status mismatch")
    if plan.connection_attempted or plan.execution_permitted:
        failures.append("Databricks plan is not dry-run safe")
    if not validate_table_contracts(plan.target_table_contracts):
        failures.append("Databricks table contracts contain unsupported Spark types")
    if plan.expected_record_counts.get("processed_documents") != manifest.processed_document_count:
        failures.append("Databricks document count mismatch")
    return failures
