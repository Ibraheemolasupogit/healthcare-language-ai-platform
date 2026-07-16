from __future__ import annotations

import csv
import filecmp
import json
from datetime import datetime
from pathlib import Path

import pytest

from healthcare_language_ai.config import PreprocessingSettings
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.preprocessing.contracts import PreprocessingMode
from healthcare_language_ai.preprocessing.databricks import (
    table_contracts,
    validate_table_contracts,
)
from healthcare_language_ai.preprocessing.normalisation import normalise_text
from healthcare_language_ai.preprocessing.pipeline import (
    derive_preprocessing_run_id,
    run_preprocessing,
)
from healthcare_language_ai.preprocessing.validation import validate_preprocessing_dir

FIXTURE_RUN_ID = "PRE-72e9829c61769cea948faacc"
INGESTION_FIXTURE = Path("tests/fixtures/ingestion/ING-92a15c8f10047400ee895203")
REFERENCE_TIMESTAMP = datetime.fromisoformat("2026-01-03T09:00:00+00:00")


def _run(tmp_path: Path, mode: PreprocessingMode = PreprocessingMode.CONSERVATIVE) -> Path:
    return run_preprocessing(
        ingestion_dir=INGESTION_FIXTURE,
        output_root=tmp_path,
        mode=mode,
        reference_timestamp=REFERENCE_TIMESTAMP,
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=PreprocessingSettings(),
    )


def test_conservative_and_analytical_preprocessing_succeed(tmp_path: Path) -> None:
    conservative = _run(tmp_path / "c", PreprocessingMode.CONSERVATIVE)
    analytical = _run(tmp_path / "a", PreprocessingMode.ANALYTICAL)
    assert validate_preprocessing_dir(conservative) == []
    assert validate_preprocessing_dir(analytical) == []
    assert conservative.name != analytical.name


def test_same_source_and_config_produce_same_run_id() -> None:
    kwargs = {
        "ingestion_manifest_checksum": "abc",
        "contract_version": "1.0.0",
        "mode": PreprocessingMode.CONSERVATIVE,
        "reference_timestamp": REFERENCE_TIMESTAMP,
        "normalisation_version": "1.0.0",
        "section_parser_version": "1.0.0",
        "sentence_segmenter_version": "1.0.0",
        "tokeniser_version": "1.0.0",
        "quality_rules_version": "1.0.0",
        "write_csv_enabled": True,
        "write_parquet_enabled": True,
    }
    assert derive_preprocessing_run_id(**kwargs) == derive_preprocessing_run_id(**kwargs)


def test_different_normalisation_version_changes_run_id() -> None:
    base = derive_preprocessing_run_id(
        ingestion_manifest_checksum="abc",
        contract_version="1.0.0",
        mode=PreprocessingMode.CONSERVATIVE,
        reference_timestamp=REFERENCE_TIMESTAMP,
        normalisation_version="1.0.0",
        section_parser_version="1.0.0",
        sentence_segmenter_version="1.0.0",
        tokeniser_version="1.0.0",
        quality_rules_version="1.0.0",
        write_csv_enabled=True,
        write_parquet_enabled=True,
    )
    changed = derive_preprocessing_run_id(
        ingestion_manifest_checksum="abc",
        contract_version="1.0.0",
        mode=PreprocessingMode.CONSERVATIVE,
        reference_timestamp=REFERENCE_TIMESTAMP,
        normalisation_version="1.0.1",
        section_parser_version="1.0.0",
        sentence_segmenter_version="1.0.0",
        tokeniser_version="1.0.0",
        quality_rules_version="1.0.0",
        write_csv_enabled=True,
        write_parquet_enabled=True,
    )
    assert base != changed


def test_source_text_is_preserved_and_offsets_are_valid() -> None:
    fixture = Path("tests/fixtures/preprocessing") / FIXTURE_RUN_ID
    with (fixture / "processed_documents.csv").open(encoding="utf-8", newline="") as stream:
        docs = {row["document_id"]: row for row in csv.DictReader(stream)}
    with (INGESTION_FIXTURE / "canonical_clinical_documents.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        source_docs = {row["document_id"]: row for row in csv.DictReader(stream)}
    assert all(docs[key]["source_text"] == source_docs[key]["document_text"] for key in docs)
    with (fixture / "processed_sections.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            text = docs[row["document_id"]]["normalised_text"]
            assert text[int(row["content_start"]) : int(row["content_end"])] == row["section_text"]
    with (fixture / "processed_sentences.csv").open(encoding="utf-8", newline="") as stream:
        previous: dict[str, int] = {}
        for row in csv.DictReader(stream):
            text = docs[row["document_id"]]["normalised_text"]
            start = int(row["start_offset"])
            end = int(row["end_offset"])
            assert text[start:end] == row["sentence_text"]
            assert start >= previous.get(row["document_id"], 0)
            previous[row["document_id"]] = end


def test_normalisation_preserves_negation_digits_units_and_identifiers() -> None:
    text = "No  oxygen saturation 98 percent for SYN-DOC-000001.\r\nLine\tend   \n"
    normalised, _ = normalise_text(
        text,
        unicode_form="NFC",
        tab_width=4,
        collapse_spaces=True,
        preserve_final_newline=True,
    )
    assert "No" in normalised
    assert "98" in normalised
    assert "percent" in normalised
    assert "SYN-DOC-000001" in normalised
    assert "\r" not in normalised


def test_projection_statuses_and_manifest_counts() -> None:
    fixture = Path("tests/fixtures/preprocessing") / FIXTURE_RUN_ID
    manifest = json.loads((fixture / "preprocessing_manifest.json").read_text())
    assert manifest["processed_document_count"] == 15
    assert manifest["section_count"] == 69
    assert manifest["sentence_count"] == 69
    assert manifest["projected_annotation_count"] == 141
    assert manifest["unresolved_annotation_count"] == 0
    assert sum(manifest["annotation_projection_status_counts"].values()) == 141
    assert manifest["annotation_projection_status_counts"]["unchanged"] == 66
    assert manifest["annotation_projection_status_counts"]["not_applicable"] == 75


def test_same_source_and_config_produce_identical_csv_and_json(tmp_path: Path) -> None:
    first = _run(tmp_path / "first")
    second = _run(tmp_path / "second")
    for file_name in [
        "processed_documents.csv",
        "processed_sections.csv",
        "processed_sentences.csv",
        "projected_annotations.csv",
        "preprocessing_manifest.json",
        "preprocessing_reconciliation.json",
        "document_quality_report.json",
        "databricks_pipeline_plan.json",
    ]:
        assert filecmp.cmp(first / file_name, second / file_name, shallow=False)


def test_tampered_processed_csv_fails_validation(tmp_path: Path) -> None:
    output = _run(tmp_path)
    with (output / "processed_documents.csv").open("a", encoding="utf-8") as stream:
        stream.write("tampered\n")
    assert any("checksum mismatch" in failure for failure in validate_preprocessing_dir(output))


def test_databricks_contracts_and_plan_are_safe() -> None:
    assert validate_table_contracts(table_contracts())
    plan = json.loads(
        (
            Path("tests/fixtures/preprocessing") / FIXTURE_RUN_ID / "databricks_pipeline_plan.json"
        ).read_text()
    )
    serialised = json.dumps(plan).lower()
    assert "access_token" not in serialised
    assert "client_secret" not in serialised
    assert "workspace_url" not in serialised
    assert plan["connection_attempted"] is False
    assert plan["execution_permitted"] is False


def test_preprocessing_fixture_matches_regenerated_fixture(tmp_path: Path) -> None:
    regenerated = _run(tmp_path)
    comparison = filecmp.dircmp(Path("tests/fixtures/preprocessing") / FIXTURE_RUN_ID, regenerated)
    assert not comparison.diff_files
    assert not comparison.left_only
    assert not comparison.right_only


def test_json_schema_validation_passes() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema_root = Path("schemas/preprocessing")
    fixture = Path("tests/fixtures/preprocessing") / FIXTURE_RUN_ID
    for schema_name, file_name in [
        ("preprocessing-manifest.schema.json", "preprocessing_manifest.json"),
        ("preprocessing-reconciliation.schema.json", "preprocessing_reconciliation.json"),
        ("document-quality-report.schema.json", "document_quality_report.json"),
        ("databricks-pipeline-plan.schema.json", "databricks_pipeline_plan.json"),
    ]:
        schema = json.loads((schema_root / schema_name).read_text())
        jsonschema.validate(json.loads((fixture / file_name).read_text()), schema)
