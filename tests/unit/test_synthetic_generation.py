from __future__ import annotations

import filecmp
import json
from datetime import datetime
from pathlib import Path

import pytest

from healthcare_language_ai.domain.enums import ClinicalDocumentType, DataClassification
from healthcare_language_ai.synthetic.generator import generate_dataset, write_dataset
from healthcare_language_ai.synthetic.validation import validate_dataset_dir, validate_records

REFERENCE_TIMESTAMP = datetime.fromisoformat("2026-01-01T09:00:00+00:00")


def _generate(count: int = 15, seed: int = 2026, types: list[ClinicalDocumentType] | None = None):
    return generate_dataset(
        count=count,
        seed=seed,
        document_types=types or list(ClinicalDocumentType),
        reference_timestamp=REFERENCE_TIMESTAMP,
        max_document_text_length=20_000,
    )


def test_same_seed_produces_identical_records() -> None:
    first = _generate().model_dump(mode="json")
    second = _generate().model_dump(mode="json")
    assert first == second


def test_different_seed_changes_generated_content() -> None:
    assert _generate(seed=2026).model_dump(mode="json") != _generate(seed=2027).model_dump(
        mode="json"
    )


def test_reference_timestamp_makes_time_generation_stable() -> None:
    dataset = _generate(count=1)
    document = dataset.records[0].document
    assert document.encounter_started_at.isoformat() == "2026-01-01T12:00:00+00:00"
    assert document.created_at.isoformat() == "2026-01-01T14:15:00+00:00"


def test_all_five_document_types_are_produced() -> None:
    types = {record.document.document_type for record in _generate().records}
    assert types == set(ClinicalDocumentType)


def test_requested_document_type_filtering_works() -> None:
    dataset = _generate(types=[ClinicalDocumentType.RADIOLOGY_REPORT])
    assert {record.document.document_type for record in dataset.records} == {
        ClinicalDocumentType.RADIOLOGY_REPORT
    }


def test_record_counts_and_identifiers_are_valid() -> None:
    records = _generate(count=10).records
    assert len(records) == 10
    assert len({record.document.document_id for record in records}) == 10
    assert all(record.document.document_id.startswith("SYN-DOC-") for record in records)
    assert all(
        record.document.metadata.synthetic_subject_id.startswith("SYN-SUBJ-") for record in records
    )
    assert all(
        record.document.metadata.synthetic_encounter_id.startswith("SYN-ENC-") for record in records
    )


def test_records_have_no_real_person_name_fields_and_are_synthetic() -> None:
    document = _generate(count=1).records[0].document
    payload = document.model_dump(mode="json")
    assert "name" not in payload
    assert "patient_name" not in payload
    assert document.data_classification is DataClassification.SYNTHETIC


def test_text_timestamps_and_chronology_are_valid() -> None:
    for record in _generate().records:
        document = record.document
        assert document.text.strip()
        assert len(document.text) <= 20_000
        assert document.created_at.tzinfo is not None
        assert document.encounter_started_at <= document.encounter_ended_at <= document.created_at


def test_annotations_have_valid_offsets() -> None:
    for record in _generate().records:
        for entity in record.annotation.entities:
            assert record.document.text[entity.start : entity.end] == entity.value


def test_maximum_document_length_is_enforced() -> None:
    with pytest.raises(ValueError, match="maximum length"):
        _generate(count=1).model_copy()
        generate_dataset(
            count=1,
            seed=2026,
            document_types=list(ClinicalDocumentType),
            reference_timestamp=REFERENCE_TIMESTAMP,
            max_document_text_length=10,
        )


def test_same_seed_produces_identical_canonical_files(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_dataset(
        dataset=_generate(),
        output_dir=first_dir,
        seed=2026,
        reference_timestamp=REFERENCE_TIMESTAMP,
    )
    write_dataset(
        dataset=_generate(),
        output_dir=second_dir,
        seed=2026,
        reference_timestamp=REFERENCE_TIMESTAMP,
    )
    comparison = filecmp.dircmp(first_dir, second_dir)
    assert not comparison.diff_files
    assert not comparison.left_only
    assert not comparison.right_only


def test_manifest_counts_and_checksums_match_files(tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    write_dataset(
        dataset=_generate(), output_dir=out, seed=2026, reference_timestamp=REFERENCE_TIMESTAMP
    )
    checks = validate_dataset_dir(out, max_document_text_length=20_000)
    assert all(check.status == "passed" for check in checks)


def test_tampered_dataset_fails_checksum_validation(tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    write_dataset(
        dataset=_generate(), output_dir=out, seed=2026, reference_timestamp=REFERENCE_TIMESTAMP
    )
    with (out / "clinical_documents.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    checks = validate_dataset_dir(out, max_document_text_length=20_000)
    assert any(
        check.name == "checksum:clinical_documents.jsonl" and check.status == "failed"
        for check in checks
    )


@pytest.mark.parametrize(
    ("text", "check_fragment"),
    [
        ("Suspicious value 123 456 7890.", "nhs_number_like"),
        ("Contact fake@example.test.", "email"),
        ("Telephone 07123 456 789.", "uk_phone"),
        ("Postcode SW1A 1AA.", "postcode"),
        ("Instruction says start taking tablets.", "start taking"),
    ],
)
def test_governance_patterns_fail_validation(text: str, check_fragment: str) -> None:
    dataset = _generate(count=1)
    record = dataset.records[0]
    record.document.text = f"{record.document.text}\n{text}\n"
    checks = validate_records([record], max_document_text_length=20_000)
    assert any(check_fragment in check.name and check.status == "failed" for check in checks)


def test_duplicate_identifiers_fail_validation() -> None:
    dataset = _generate(count=2)
    dataset.records[1].document.document_id = dataset.records[0].document.document_id
    checks = validate_records(dataset.records, max_document_text_length=20_000)
    assert any(check.name == "unique_document_ids" and check.status == "failed" for check in checks)


def test_output_directory_with_unknown_file_fails(tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    out.mkdir()
    (out / "manual.txt").write_text("do not overwrite\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-generated files"):
        write_dataset(
            dataset=_generate(), output_dir=out, seed=2026, reference_timestamp=REFERENCE_TIMESTAMP
        )


def test_generated_fixture_matches_regenerated_fixture(tmp_path: Path) -> None:
    fixture_dir = Path("tests/fixtures/synthetic")
    regenerated = tmp_path / "synthetic"
    write_dataset(
        dataset=_generate(),
        output_dir=regenerated,
        seed=2026,
        reference_timestamp=REFERENCE_TIMESTAMP,
    )
    comparison = filecmp.dircmp(fixture_dir, regenerated)
    assert not comparison.diff_files
    assert not comparison.left_only
    assert not comparison.right_only


def test_fixture_schema_version_and_manifest_values() -> None:
    manifest = json.loads(Path("tests/fixtures/synthetic/dataset_manifest.json").read_text())
    assert manifest["record_count"] == 15
    assert manifest["seed"] == 2026
    assert manifest["generator_version"] == "1.0.0"
    assert manifest["template_version"] == "1.0.0"
    assert manifest["vocabulary_version"] == "1.0.0"
    assert manifest["synthetic_data_only"] is True


def test_json_schema_validation_passes() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema_root = Path("schemas/synthetic")
    fixture_root = Path("tests/fixtures/synthetic")
    document_schema = json.loads((schema_root / "clinical-document.schema.json").read_text())
    annotation_schema = json.loads((schema_root / "document-annotation.schema.json").read_text())
    manifest_schema = json.loads((schema_root / "dataset-manifest.schema.json").read_text())
    quality_schema = json.loads((schema_root / "data-quality-report.schema.json").read_text())
    for line in (fixture_root / "clinical_documents.jsonl").read_text().splitlines():
        jsonschema.validate(json.loads(line), document_schema)
    for line in (fixture_root / "document_annotations.jsonl").read_text().splitlines():
        jsonschema.validate(json.loads(line), annotation_schema)
    jsonschema.validate(
        json.loads((fixture_root / "dataset_manifest.json").read_text()), manifest_schema
    )
    jsonschema.validate(
        json.loads((fixture_root / "data_quality_report.json").read_text()), quality_schema
    )
