"""Deterministic local rule-based extraction pipeline."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

import pyarrow

from healthcare_language_ai.config import ExtractionSettings
from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.extraction.classifier import classify_documents, classify_sections
from healthcare_language_ai.extraction.contracts import (
    CandidateSummary,
    EntityPrediction,
    ExtractionManifest,
    ExtractionRunStatus,
    PredictionScope,
)
from healthcare_language_ai.extraction.matcher import match_candidates
from healthcare_language_ai.extraction.overlap import resolve_overlaps
from healthcare_language_ai.extraction.reconciliation import (
    build_reconciliation_report,
    count_by,
)
from healthcare_language_ai.extraction.rules import (
    CLASSIFICATION_RULE_VERSION,
    ENTITY_RULE_VERSION,
    OVERLAP_RESOLUTION_VERSION,
    build_entity_rules,
)
from healthcare_language_ai.extraction.serialisation import (
    DOCUMENT_CLASSIFICATION_COLUMNS,
    ENTITY_COLUMNS,
    SECTION_CLASSIFICATION_COLUMNS,
    write_csv,
    write_json_model,
    write_jsonl,
    write_parquet,
)
from healthcare_language_ai.extraction.vocabularies import VOCABULARY_VERSION, load_vocabulary
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.preprocessing.contracts import (
    ProcessedClinicalDocument,
    ProcessedSection,
    ProcessedSentence,
    ProjectedAnnotation,
)
from healthcare_language_ai.preprocessing.pipeline import load_preprocessing_manifest
from healthcare_language_ai.preprocessing.validation import validate_preprocessing_dir
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_extraction_run_id(
    *,
    preprocessing_manifest_checksum: str,
    extraction_contract_version: str,
    entity_rule_version: str,
    classification_rule_version: str,
    overlap_resolution_version: str,
    vocabulary_version: str,
    text_representation: str,
    reference_timestamp: datetime,
    write_csv_enabled: bool,
    write_parquet_enabled: bool,
) -> str:
    value = deterministic_id(
        {
            "preprocessing_manifest_checksum": preprocessing_manifest_checksum,
            "extraction_contract_version": extraction_contract_version,
            "entity_rule_version": entity_rule_version,
            "classification_rule_version": classification_rule_version,
            "overlap_resolution_version": overlap_resolution_version,
            "vocabulary_version": vocabulary_version,
            "text_representation": text_representation,
            "reference_timestamp": reference_timestamp.isoformat(),
            "write_csv": write_csv_enabled,
            "write_parquet": write_parquet_enabled,
        },
        length=24,
    )
    return f"EXT-{value}"


def _prepare_output_dir(output_dir: Path, policy: OverwritePolicy) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if policy is OverwritePolicy.FAIL_IF_EXISTS:
        msg = f"output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _load_documents(path: Path) -> list[ProcessedClinicalDocument]:
    return [ProcessedClinicalDocument.model_validate(row) for row in _read_csv(path)]


def _load_sections(path: Path) -> list[ProcessedSection]:
    return [ProcessedSection.model_validate(row) for row in _read_csv(path)]


def _load_sentences(path: Path) -> list[ProcessedSentence]:
    return [ProcessedSentence.model_validate(row) for row in _read_csv(path)]


def _load_projected_annotations(path: Path) -> list[ProjectedAnnotation]:
    rows = []
    for row in _read_csv(path):
        for key in ("source_start", "source_end", "target_start", "target_end"):
            if row[key] == "":
                row[key] = None  # type: ignore[assignment]
        rows.append(ProjectedAnnotation.model_validate(row))
    return rows


def _prediction_from_candidate(candidate) -> EntityPrediction:  # type: ignore[no-untyped-def]
    prediction_id = "PRED_" + deterministic_id(
        {
            "run": candidate.extraction_run_id,
            "document_id": candidate.document_id,
            "label": candidate.label,
            "start": candidate.start_offset,
            "end": candidate.end_offset,
            "rule_id": candidate.rule_id,
        },
        length=24,
    )
    return EntityPrediction(
        prediction_id=prediction_id,
        document_id=candidate.document_id,
        label=candidate.label,
        value=candidate.value,
        normalised_value=candidate.normalised_value,
        start_offset=candidate.start_offset,
        end_offset=candidate.end_offset,
        prediction_scope=PredictionScope.SPAN,
        confidence=candidate.confidence,
        rule_id=candidate.rule_id,
        rule_version=candidate.rule_version,
        vocabulary_version=candidate.vocabulary_version,
        matched_text=candidate.matched_text,
        source_text_representation="normalised_text",
        section_id=candidate.section_id,
        sentence_id=candidate.sentence_id,
        preprocessing_run_id=candidate.preprocessing_run_id,
        extraction_run_id=candidate.extraction_run_id,
    )


def run_extraction(
    *,
    preprocessing_dir: Path,
    output_root: Path,
    text_representation: str,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: ExtractionSettings,
) -> Path:
    failures = validate_preprocessing_dir(preprocessing_dir)
    if failures:
        msg = f"preprocessing evidence failed validation: {failures[0]}"
        raise DataGovernanceError(msg)
    if text_representation != "normalised_text":
        msg = "only normalised_text extraction is supported in Milestone 5"
        raise ValueError(msg)
    preprocessing_manifest = load_preprocessing_manifest(preprocessing_dir)
    if (
        not preprocessing_manifest.synthetic_data_only
        or not preprocessing_manifest.clinical_use_prohibited
    ):
        msg = "source preprocessing governance flags are unsafe"
        raise DataGovernanceError(msg)
    if (
        preprocessing_manifest.processed_document_count
        > settings.maximum_documents_per_extraction_run
    ):
        msg = "source document count exceeds configured extraction maximum"
        raise DataGovernanceError(msg)

    preprocessing_manifest_checksum = sha256_file(preprocessing_dir / "preprocessing_manifest.json")
    extraction_run_id = derive_extraction_run_id(
        preprocessing_manifest_checksum=preprocessing_manifest_checksum,
        extraction_contract_version=settings.extraction_contract_version,
        entity_rule_version=settings.entity_rule_version,
        classification_rule_version=settings.classification_rule_version,
        overlap_resolution_version=settings.overlap_resolution_version,
        vocabulary_version=settings.vocabulary_version,
        text_representation=text_representation,
        reference_timestamp=reference_timestamp,
        write_csv_enabled=settings.write_csv,
        write_parquet_enabled=settings.write_parquet,
    )
    output_dir = output_root / extraction_run_id
    _prepare_output_dir(output_dir, overwrite_policy)

    documents = _load_documents(preprocessing_dir / "processed_documents.csv")
    sections = _load_sections(preprocessing_dir / "processed_sections.csv")
    sentences = _load_sentences(preprocessing_dir / "processed_sentences.csv")
    annotations = _load_projected_annotations(preprocessing_dir / "projected_annotations.csv")
    entries = load_vocabulary()
    rules = build_entity_rules(entries)
    candidates = match_candidates(
        documents=documents,
        sections=sections,
        sentences=sentences,
        entries=entries,
        rules=rules,
        extraction_run_id=extraction_run_id,
    )
    accepted, suppressed, duplicate_count = resolve_overlaps(candidates)
    predictions = [_prediction_from_candidate(candidate) for candidate in accepted]
    classifications = classify_documents(
        documents=documents,
        sections=sections,
        extraction_run_id=extraction_run_id,
    )
    section_classifications = classify_sections(
        sections=sections, extraction_run_id=extraction_run_id
    )
    candidate_summary = CandidateSummary(
        extraction_run_id=extraction_run_id,
        candidate_count=len(candidates),
        accepted_count=len(predictions),
        suppressed_overlap_count=len(suppressed),
        duplicate_prediction_count=duplicate_count,
        candidate_count_by_label=count_by([item.label for item in candidates]),
        accepted_count_by_label=count_by([item.label for item in predictions]),
    )

    if settings.write_csv:
        write_csv(output_dir / "entity_predictions.csv", predictions, ENTITY_COLUMNS)
        write_csv(
            output_dir / "document_classifications.csv",
            classifications,
            DOCUMENT_CLASSIFICATION_COLUMNS,
        )
        write_csv(
            output_dir / "section_classifications.csv",
            section_classifications,
            SECTION_CLASSIFICATION_COLUMNS,
        )
    if settings.write_parquet:
        write_parquet(
            output_dir / "entity_predictions.parquet",
            predictions,
            ENTITY_COLUMNS,
            compression="zstd",
        )
        write_parquet(
            output_dir / "document_classifications.parquet",
            classifications,
            DOCUMENT_CLASSIFICATION_COLUMNS,
            compression="zstd",
        )
        write_parquet(
            output_dir / "section_classifications.parquet",
            section_classifications,
            SECTION_CLASSIFICATION_COLUMNS,
            compression="zstd",
        )
    write_json_model(output_dir / "candidate_summary.json", candidate_summary)
    write_jsonl(output_dir / "suppressed_candidates.jsonl", suppressed)
    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "extraction_manifest.json"
    }
    reconciliation = build_reconciliation_report(
        extraction_run_id=extraction_run_id,
        documents=documents,
        candidates=candidates,
        predictions=predictions,
        classifications=classifications,
        suppressed=suppressed,
        duplicate_prediction_count=duplicate_count,
        output_checksum_status=True,
    )
    write_json_model(output_dir / "extraction_reconciliation.json", reconciliation)
    output_checksums["extraction_reconciliation.json"] = sha256_file(
        output_dir / "extraction_reconciliation.json"
    )
    manifest = ExtractionManifest(
        manifest_schema_version="1.0.0",
        extraction_contract_version=settings.extraction_contract_version,
        extraction_run_id=extraction_run_id,
        run_status=ExtractionRunStatus.COMPLETED
        if reconciliation.overall_status == "passed"
        else ExtractionRunStatus.COMPLETED_WITH_WARNINGS,
        source_preprocessing_run_id=preprocessing_manifest.preprocessing_run_id,
        source_preprocessing_manifest_checksum=preprocessing_manifest_checksum,
        source_document_count=preprocessing_manifest.processed_document_count,
        source_section_count=preprocessing_manifest.section_count,
        source_sentence_count=preprocessing_manifest.sentence_count,
        source_annotation_count=len(annotations),
        entity_prediction_count=len(predictions),
        document_classification_count=len(classifications),
        section_classification_count=len(section_classifications),
        candidate_count=len(candidates),
        suppressed_overlap_count=len(suppressed),
        duplicate_prediction_count=duplicate_count,
        prediction_scope_counts=count_by([item.prediction_scope.value for item in predictions]),
        prediction_label_counts=count_by([item.label for item in predictions]),
        document_type_prediction_counts=count_by(
            [item.predicted_document_type for item in classifications]
        ),
        entity_rule_version=ENTITY_RULE_VERSION,
        classification_rule_version=CLASSIFICATION_RULE_VERSION,
        overlap_resolution_version=OVERLAP_RESOLUTION_VERSION,
        vocabulary_version=VOCABULARY_VERSION,
        text_representation="normalised_text",
        reference_timestamp=reference_timestamp,
        writer_versions={"pyarrow": pyarrow.__version__, "csv": "python-stdlib"},
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status=reconciliation.overall_status,
    )
    write_json_model(output_dir / "extraction_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        "# Rule-Based Extraction Evidence\n\n"
        f"Run ID: {extraction_run_id}\n"
        "No MLflow, Databricks or model connection was attempted.\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def load_extraction_manifest(extraction_dir: Path) -> ExtractionManifest:
    return ExtractionManifest.model_validate(read_json(extraction_dir / "extraction_manifest.json"))
