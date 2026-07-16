"""Validation for persisted ingestion evidence."""

from __future__ import annotations

import csv
from pathlib import Path

from healthcare_language_ai.ingestion.contracts import (
    IngestionManifest,
    ReconciliationReport,
    SnowflakeLoadPlan,
)
from healthcare_language_ai.ingestion.serialisation import parquet_row_count, parquet_schema_names
from healthcare_language_ai.ingestion.snowflake import validate_table_contracts
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return max(sum(1 for _ in csv.DictReader(stream)), 0)


def validate_ingestion_dir(ingestion_dir: Path) -> list[str]:
    """Return validation failure messages for an ingestion evidence directory."""
    failures: list[str] = []
    manifest = IngestionManifest.model_validate(
        read_json(ingestion_dir / "ingestion_manifest.json")
    )
    reconciliation = ReconciliationReport.model_validate(
        read_json(ingestion_dir / "reconciliation_report.json")
    )
    plan = SnowflakeLoadPlan.model_validate(read_json(ingestion_dir / "snowflake_load_plan.json"))
    for file_name, expected in manifest.output_file_checksums.items():
        path = ingestion_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            failures.append(f"checksum mismatch: {file_name}")
    doc_csv = ingestion_dir / "canonical_clinical_documents.csv"
    ann_csv = ingestion_dir / "canonical_document_annotations.csv"
    if doc_csv.exists() and csv_row_count(doc_csv) != manifest.canonical_document_count:
        failures.append("document CSV row count mismatch")
    if ann_csv.exists() and csv_row_count(ann_csv) != manifest.canonical_annotation_count:
        failures.append("annotation CSV row count mismatch")
    doc_parquet = ingestion_dir / "canonical_clinical_documents.parquet"
    ann_parquet = ingestion_dir / "canonical_document_annotations.parquet"
    if doc_parquet.exists() and parquet_row_count(doc_parquet) != manifest.canonical_document_count:
        failures.append("document Parquet row count mismatch")
    if (
        ann_parquet.exists()
        and parquet_row_count(ann_parquet) != manifest.canonical_annotation_count
    ):
        failures.append("annotation Parquet row count mismatch")
    if doc_parquet.exists() and "document_id" not in parquet_schema_names(doc_parquet):
        failures.append("document Parquet schema missing document_id")
    if reconciliation.overall_status != manifest.reconciliation_status:
        failures.append("reconciliation status mismatch")
    if not plan.execution_prohibited or not plan.no_connection_attempted:
        failures.append("Snowflake plan does not clearly prohibit execution")
    if not validate_table_contracts(plan.target_tables):
        failures.append("Snowflake table contracts contain unsupported types")
    if plan.expected_row_counts.get("RAW_CLINICAL_DOCUMENTS") != manifest.canonical_document_count:
        failures.append("Snowflake document row count mismatch")
    if (
        plan.expected_row_counts.get("RAW_DOCUMENT_ANNOTATIONS")
        != manifest.canonical_annotation_count
    ):
        failures.append("Snowflake annotation row count mismatch")
    if not manifest.synthetic_data_only or not manifest.clinical_use_prohibited:
        failures.append("manifest governance flags are unsafe")
    return failures
