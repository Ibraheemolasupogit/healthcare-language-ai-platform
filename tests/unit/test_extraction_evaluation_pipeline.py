from __future__ import annotations

import csv
import filecmp
import json
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import validate

from healthcare_language_ai.config import EvaluationSettings, ExtractionSettings
from healthcare_language_ai.evaluation.pipeline import derive_evaluation_run_id, run_evaluation
from healthcare_language_ai.evaluation.validation import validate_evaluation_dir
from healthcare_language_ai.extraction.overlap import resolve_overlaps
from healthcare_language_ai.extraction.pipeline import derive_extraction_run_id, run_extraction
from healthcare_language_ai.extraction.validation import validate_extraction_dir
from healthcare_language_ai.extraction.vocabularies import load_vocabulary
from healthcare_language_ai.ingestion.contracts import OverwritePolicy

PREPROCESSING_FIXTURE = Path("tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc")
EXTRACTION_FIXTURE = Path("tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d")
EVALUATION_FIXTURE = Path("tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605")
EXTRACTION_TS = datetime.fromisoformat("2026-01-04T09:00:00+00:00")
EVALUATION_TS = datetime.fromisoformat("2026-01-05T09:00:00+00:00")


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_vocabulary_loads_deterministically_and_uses_supported_labels() -> None:
    first = load_vocabulary()
    second = load_vocabulary()
    assert [item.vocabulary_entry_id for item in first] == [
        item.vocabulary_entry_id for item in second
    ]
    assert len({item.vocabulary_entry_id for item in first}) == len(first)
    assert {item.label for item in first} == {
        "administrative_priority",
        "body_site",
        "descriptor",
        "encounter_context",
        "investigation",
        "observation",
        "presenting_concern",
        "specialty",
        "workflow_status",
    }


def test_extraction_fixture_predictions_have_valid_offsets_and_bounded_confidence() -> None:
    docs = {
        row["document_id"]: row
        for row in _csv_rows(PREPROCESSING_FIXTURE / "processed_documents.csv")
    }
    rows = _csv_rows(EXTRACTION_FIXTURE / "entity_predictions.csv")
    assert len(rows) == 66
    for row in rows:
        start = int(row["start_offset"])
        end = int(row["end_offset"])
        assert row["prediction_scope"] == "span"
        assert row["matched_text"] == docs[row["document_id"]]["normalised_text"][start:end]
        assert 0 <= float(row["confidence"]) <= 1


def test_document_classification_is_complete_and_heading_based() -> None:
    rows = _csv_rows(EXTRACTION_FIXTURE / "document_classifications.csv")
    assert len(rows) == 15
    assert {row["predicted_document_type"] for row in rows} == {
        "clinical_note",
        "discharge_summary",
        "pathology_report",
        "radiology_report",
        "referral_letter",
    }
    assert all(row["matched_rule_ids"] for row in rows)


def test_extraction_run_id_changes_with_rule_version() -> None:
    kwargs = {
        "preprocessing_manifest_checksum": "abc",
        "extraction_contract_version": "1.0.0",
        "entity_rule_version": "1.0.0",
        "classification_rule_version": "1.0.0",
        "overlap_resolution_version": "1.0.0",
        "vocabulary_version": "1.0.0",
        "text_representation": "normalised_text",
        "reference_timestamp": EXTRACTION_TS,
        "write_csv_enabled": True,
        "write_parquet_enabled": True,
    }
    assert derive_extraction_run_id(**kwargs) != derive_extraction_run_id(
        **{**kwargs, "entity_rule_version": "1.0.1"}
    )


def test_extraction_fixture_is_reproducible(tmp_path: Path) -> None:
    generated = run_extraction(
        preprocessing_dir=PREPROCESSING_FIXTURE,
        output_root=tmp_path,
        text_representation="normalised_text",
        reference_timestamp=EXTRACTION_TS,
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=ExtractionSettings(),
    )
    assert filecmp.cmp(
        EXTRACTION_FIXTURE / "entity_predictions.csv",
        generated / "entity_predictions.csv",
        shallow=False,
    )
    assert validate_extraction_dir(generated) == []


def test_evaluation_metrics_and_accounting_are_computed() -> None:
    manifest = json.loads((EVALUATION_FIXTURE / "evaluation_manifest.json").read_text())
    assert manifest["true_positive_count"] == 66
    assert manifest["false_positive_count"] == 0
    assert manifest["false_negative_count"] == 0
    assert manifest["micro_f1"] == 1.0
    assert manifest["classification_accuracy"] == 1.0
    assert (
        manifest["true_positive_count"] + manifest["false_negative_count"]
        == manifest["evaluated_ground_truth_count"]
    )
    assert (
        manifest["true_positive_count"] + manifest["false_positive_count"]
        == manifest["evaluated_prediction_count"]
    )


def test_evaluation_fixture_is_reproducible(tmp_path: Path) -> None:
    generated = run_evaluation(
        extraction_dir=EXTRACTION_FIXTURE,
        preprocessing_dir=PREPROCESSING_FIXTURE,
        output_root=tmp_path,
        matching_policy="exact",
        reference_timestamp=EVALUATION_TS,
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=EvaluationSettings(),
    )
    assert filecmp.cmp(
        EVALUATION_FIXTURE / "evaluation_manifest.json",
        generated / "evaluation_manifest.json",
        shallow=False,
    )
    assert validate_evaluation_dir(generated) == []


def test_evaluation_run_id_changes_with_matching_policy() -> None:
    kwargs = {
        "extraction_manifest_checksum": "abc",
        "ground_truth_checksum": "def",
        "evaluation_contract_version": "1.0.0",
        "metrics_version": "1.0.0",
        "matching_policy": "exact",
        "relaxed_overlap_threshold": 0.5,
        "reference_timestamp": EVALUATION_TS,
    }
    assert derive_evaluation_run_id(**kwargs) != derive_evaluation_run_id(
        **{**kwargs, "matching_policy": "relaxed_overlap"}
    )


def test_model_card_and_mlflow_plan_are_safe() -> None:
    card = json.loads((EVALUATION_FIXTURE / "baseline_model_card.json").read_text())
    plan = json.loads((EVALUATION_FIXTURE / "mlflow_experiment_plan.json").read_text())
    assert "Vocabulary overlap" in card["known_limitations"][1]
    assert plan["connection_attempted"] is False
    assert plan["execution_permitted"] is False
    assert "tracking_uri" not in json.dumps(plan).casefold()


def test_json_schemas_validate_fixture_evidence() -> None:
    validate(
        json.loads((EXTRACTION_FIXTURE / "extraction_manifest.json").read_text()),
        json.loads(Path("schemas/extraction/extraction-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((EVALUATION_FIXTURE / "evaluation_manifest.json").read_text()),
        json.loads(Path("schemas/evaluation/evaluation-manifest.schema.json").read_text()),
    )


def test_tampered_extraction_file_fails_validation(tmp_path: Path) -> None:
    generated = run_extraction(
        preprocessing_dir=PREPROCESSING_FIXTURE,
        output_root=tmp_path,
        text_representation="normalised_text",
        reference_timestamp=EXTRACTION_TS,
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=ExtractionSettings(),
    )
    with (generated / "entity_predictions.csv").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    assert validate_extraction_dir(generated)


def test_invalid_matching_policy_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported matching policy"):
        run_evaluation(
            extraction_dir=EXTRACTION_FIXTURE,
            preprocessing_dir=PREPROCESSING_FIXTURE,
            output_root=tmp_path,
            matching_policy="unsupported",
            reference_timestamp=EVALUATION_TS,
            overwrite_policy=OverwritePolicy.FORCE_REPLACE,
            settings=EvaluationSettings(),
        )


def test_overlap_resolution_prefers_higher_priority() -> None:
    candidates = []
    with (EXTRACTION_FIXTURE / "entity_predictions.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        row = next(csv.DictReader(stream))
    from healthcare_language_ai.extraction.contracts import RuleMatch

    base = {
        "document_id": row["document_id"],
        "label": row["label"],
        "value": row["value"],
        "normalised_value": row["normalised_value"],
        "start_offset": int(row["start_offset"]),
        "end_offset": int(row["end_offset"]),
        "matched_text": row["matched_text"],
        "section_id": row["section_id"],
        "section_label": "x",
        "sentence_id": row["sentence_id"],
        "rule_version": "1.0.0",
        "vocabulary_entry_id": "VOC_x",
        "vocabulary_version": "1.0.0",
        "confidence": 0.9,
        "text_representation": "normalised_text",
        "preprocessing_run_id": "PRE",
        "extraction_run_id": "EXT",
    }
    candidates.append(RuleMatch(candidate_id="low", rule_id="RULE_b", priority=1, **base))
    candidates.append(RuleMatch(candidate_id="high", rule_id="RULE_a", priority=2, **base))
    accepted, suppressed, duplicates = resolve_overlaps(candidates)
    assert accepted[0].candidate_id == "high"
    assert suppressed == []
    assert duplicates == 1
