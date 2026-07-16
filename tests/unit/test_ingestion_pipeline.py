from __future__ import annotations

import csv
import filecmp
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from healthcare_language_ai.config import IngestionSettings
from healthcare_language_ai.exceptions import ConfigurationError, DataGovernanceError
from healthcare_language_ai.ingestion.contracts import IngestionMode, OverwritePolicy
from healthcare_language_ai.ingestion.discovery import discover_source
from healthcare_language_ai.ingestion.pipeline import derive_ingestion_run_id, run_ingestion
from healthcare_language_ai.ingestion.quality import validate_ingestion_dir
from healthcare_language_ai.ingestion.serialisation import parquet_row_count, parquet_schema_names
from healthcare_language_ai.ingestion.snowflake import table_contracts, validate_table_contracts

REFERENCE_TIMESTAMP = datetime.fromisoformat("2026-01-02T09:00:00+00:00")
FIXTURE_RUN_ID = "ING-92a15c8f10047400ee895203"


def _settings() -> IngestionSettings:
    return IngestionSettings()


def _run(tmp_path: Path, source_dir: Path = Path("tests/fixtures/synthetic")) -> Path:
    return run_ingestion(
        source_dir=source_dir,
        output_root=tmp_path,
        mode=IngestionMode.STRICT,
        reference_timestamp=REFERENCE_TIMESTAMP,
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=_settings(),
        max_document_text_length=20_000,
    )


def _copy_source(tmp_path: Path) -> Path:
    target = tmp_path / "synthetic"
    shutil.copytree("tests/fixtures/synthetic", target)
    return target


def test_valid_milestone_2_fixture_is_discovered() -> None:
    source = discover_source(Path("tests/fixtures/synthetic"), follow_symlinks=False)
    assert source.source_manifest_checksum
    assert {file.file_name for file in source.files} >= {"clinical_documents.jsonl"}


def test_missing_required_source_file_fails(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    (source / "README.md").unlink()
    with pytest.raises(ConfigurationError):
        discover_source(source, follow_symlinks=False)


def test_manifest_checksum_mismatch_fails(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    manifest = json.loads((source / "dataset_manifest.json").read_text())
    manifest["file_checksums"]["clinical_documents.jsonl"] = "bad"
    (source / "dataset_manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    with pytest.raises(DataGovernanceError):
        _run(tmp_path / "out", source)


def test_failed_source_quality_report_fails(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    quality = json.loads((source / "data_quality_report.json").read_text())
    quality["validation_status"] = "failed"
    (source / "data_quality_report.json").write_text(json.dumps(quality, sort_keys=True) + "\n")
    with pytest.raises(DataGovernanceError):
        _run(tmp_path / "out", source)


def test_non_synthetic_source_flag_fails(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    manifest = json.loads((source / "dataset_manifest.json").read_text())
    manifest["synthetic_data_only"] = False
    (source / "dataset_manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    with pytest.raises(DataGovernanceError):
        _run(tmp_path / "out", source)


def test_strict_ingestion_succeeds_for_valid_fixture(tmp_path: Path) -> None:
    output = _run(tmp_path)
    assert output.name == FIXTURE_RUN_ID
    assert validate_ingestion_dir(output) == []


def test_same_source_and_config_produce_same_run_id() -> None:
    kwargs = {
        "source_manifest_checksum": "abc",
        "contract_version": "1.0.0",
        "mode": IngestionMode.STRICT,
        "reference_timestamp": REFERENCE_TIMESTAMP,
        "write_csv_enabled": True,
        "write_parquet_enabled": True,
    }
    assert derive_ingestion_run_id(**kwargs) == derive_ingestion_run_id(**kwargs)


def test_different_source_checksum_or_mode_changes_run_id() -> None:
    base = derive_ingestion_run_id(
        source_manifest_checksum="abc",
        contract_version="1.0.0",
        mode=IngestionMode.STRICT,
        reference_timestamp=REFERENCE_TIMESTAMP,
        write_csv_enabled=True,
        write_parquet_enabled=True,
    )
    changed_source = derive_ingestion_run_id(
        source_manifest_checksum="def",
        contract_version="1.0.0",
        mode=IngestionMode.STRICT,
        reference_timestamp=REFERENCE_TIMESTAMP,
        write_csv_enabled=True,
        write_parquet_enabled=True,
    )
    changed_mode = derive_ingestion_run_id(
        source_manifest_checksum="abc",
        contract_version="1.0.0",
        mode=IngestionMode.QUARANTINE,
        reference_timestamp=REFERENCE_TIMESTAMP,
        write_csv_enabled=True,
        write_parquet_enabled=True,
    )
    assert base != changed_source
    assert base != changed_mode


def test_same_source_and_config_produce_identical_csv_and_json(tmp_path: Path) -> None:
    first = _run(tmp_path / "first")
    second = _run(tmp_path / "second")
    for file_name in [
        "canonical_clinical_documents.csv",
        "canonical_document_annotations.csv",
        "ingestion_manifest.json",
        "reconciliation_report.json",
        "snowflake_load_plan.json",
    ]:
        assert filecmp.cmp(first / file_name, second / file_name, shallow=False)


def test_counts_lineage_offsets_and_foreign_keys() -> None:
    fixture = Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID
    manifest = json.loads((fixture / "ingestion_manifest.json").read_text())
    assert manifest["canonical_document_count"] == 15
    assert manifest["canonical_annotation_count"] == 141
    document_csv = fixture / "canonical_clinical_documents.csv"
    annotation_csv = fixture / "canonical_document_annotations.csv"
    with document_csv.open(encoding="utf-8", newline="") as stream:
        docs = {row["document_id"]: row for row in csv.DictReader(stream)}
    with annotation_csv.open(encoding="utf-8", newline="") as stream:
        annotations = list(csv.DictReader(stream))
    assert all(row["source_file"] == "clinical_documents.jsonl" for row in docs.values())
    assert all(row["document_id"] in docs for row in annotations)
    for row in annotations:
        if row["annotation_type"] == "span":
            text = docs[row["document_id"]]["document_text"]
            assert text[int(row["start_offset"]) : int(row["end_offset"])] == row["value"]
        else:
            assert row["start_offset"] == ""
            assert row["end_offset"] == ""


def test_csv_contract_and_lf_newline_roundtrip() -> None:
    fixture = Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID
    csv_path = fixture / "canonical_clinical_documents.csv"
    raw = csv_path.read_bytes()
    assert b"\r\n" not in raw
    with csv_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert list(rows[0])[:4] == [
        "document_id",
        "synthetic_subject_id",
        "synthetic_encounter_id",
        "document_type",
    ]
    assert "\n" in rows[0]["document_text"]


def test_parquet_schema_and_counts_match_csv() -> None:
    fixture = Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID
    assert parquet_row_count(fixture / "canonical_clinical_documents.parquet") == 15
    assert parquet_row_count(fixture / "canonical_document_annotations.parquet") == 141
    schema_names = parquet_schema_names(fixture / "canonical_clinical_documents.parquet")
    assert schema_names[0] == "document_id"


def test_tampered_csv_fails_validation(tmp_path: Path) -> None:
    output = _run(tmp_path)
    with (output / "canonical_clinical_documents.csv").open("a", encoding="utf-8") as stream:
        stream.write("tampered\n")
    assert any("checksum mismatch" in failure for failure in validate_ingestion_dir(output))


def test_snowflake_table_contracts_use_supported_types() -> None:
    contracts = table_contracts("HEALTHCARE_LANGUAGE_AI", "RAW", "STAGING", "GOVERNANCE")
    assert validate_table_contracts(contracts)
    assert {table.table_name for table in contracts} >= {"RAW_CLINICAL_DOCUMENTS"}


def test_snowflake_plan_contains_no_credentials_and_no_connection() -> None:
    plan = json.loads(
        (Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID / "snowflake_load_plan.json").read_text()
    )
    serialised = json.dumps(plan).lower()
    assert "password" not in serialised
    assert "private_key" not in serialised
    assert plan["execution_prohibited"] is True
    assert plan["no_connection_attempted"] is True


def test_checked_in_ingestion_fixture_matches_regenerated_fixture(tmp_path: Path) -> None:
    regenerated_root = tmp_path / "ingestion"
    regenerated = _run(regenerated_root)
    comparison = filecmp.dircmp(Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID, regenerated)
    assert not comparison.diff_files
    assert not comparison.left_only
    assert not comparison.right_only


def test_json_schema_validation_passes() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema_root = Path("schemas/ingestion")
    fixture = Path("tests/fixtures/ingestion") / FIXTURE_RUN_ID
    for schema_name, file_name in [
        ("ingestion-manifest.schema.json", "ingestion_manifest.json"),
        ("reconciliation-report.schema.json", "reconciliation_report.json"),
        ("snowflake-load-plan.schema.json", "snowflake_load_plan.json"),
    ]:
        schema = json.loads((schema_root / schema_name).read_text())
        jsonschema.validate(json.loads((fixture / file_name).read_text()), schema)
