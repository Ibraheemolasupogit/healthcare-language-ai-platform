"""Validation for persisted extraction evidence."""

from __future__ import annotations

import csv
from pathlib import Path

from healthcare_language_ai.extraction.contracts import (
    SUPPORTED_DOCUMENT_TYPES,
    SUPPORTED_ENTITY_LABELS,
    CandidateSummary,
    ExtractionManifest,
    PredictionReconciliationReport,
)
from healthcare_language_ai.extraction.serialisation import parquet_row_count
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_extraction_dir(extraction_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = ExtractionManifest.model_validate(
        read_json(extraction_dir / "extraction_manifest.json")
    )
    reconciliation = PredictionReconciliationReport.model_validate(
        read_json(extraction_dir / "extraction_reconciliation.json")
    )
    CandidateSummary.model_validate(read_json(extraction_dir / "candidate_summary.json"))
    for file_name, expected_checksum in manifest.output_file_checksums.items():
        path = extraction_dir / file_name
        if not path.exists():
            failures.append(f"missing output file: {file_name}")
        elif sha256_file(path) != expected_checksum:
            failures.append(f"checksum mismatch: {file_name}")
    checks = {
        "entity_predictions": manifest.entity_prediction_count,
        "document_classifications": manifest.document_classification_count,
        "section_classifications": manifest.section_classification_count,
    }
    for stem, expected_count in checks.items():
        csv_path = extraction_dir / f"{stem}.csv"
        parquet_path = extraction_dir / f"{stem}.parquet"
        if csv_path.exists() and len(_csv_rows(csv_path)) != expected_count:
            failures.append(f"CSV row count mismatch: {stem}")
        if parquet_path.exists() and parquet_row_count(parquet_path) != expected_count:
            failures.append(f"Parquet row count mismatch: {stem}")
    prediction_ids: set[str] = set()
    for row in _csv_rows(extraction_dir / "entity_predictions.csv"):
        if row["prediction_id"] in prediction_ids:
            failures.append("duplicate prediction_id")
        prediction_ids.add(row["prediction_id"])
        if row["label"] not in SUPPORTED_ENTITY_LABELS:
            failures.append(f"unsupported prediction label: {row['label']}")
        if row["prediction_scope"] == "span" and (not row["start_offset"] or not row["end_offset"]):
            failures.append(f"span prediction missing offsets: {row['prediction_id']}")
        confidence = float(row["confidence"])
        if confidence < 0 or confidence > 1:
            failures.append(f"confidence out of bounds: {row['prediction_id']}")
    for row in _csv_rows(extraction_dir / "document_classifications.csv"):
        if row["predicted_document_type"] not in SUPPORTED_DOCUMENT_TYPES:
            failures.append(f"unsupported document type: {row['predicted_document_type']}")
    if reconciliation.overall_status != manifest.reconciliation_status:
        failures.append("reconciliation status mismatch")
    if reconciliation.overall_status == "failed":
        failures.append("extraction reconciliation failed")
    return failures
