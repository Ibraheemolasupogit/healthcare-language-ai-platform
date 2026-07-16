"""Deterministic local preprocessing pipeline."""

from __future__ import annotations

import csv
import shutil
from datetime import datetime
from pathlib import Path

import pyarrow

from healthcare_language_ai.config import PreprocessingSettings
from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.ingestion.contracts import CanonicalDocumentAnnotation, OverwritePolicy
from healthcare_language_ai.ingestion.pipeline import load_ingestion_manifest
from healthcare_language_ai.ingestion.quality import validate_ingestion_dir
from healthcare_language_ai.preprocessing.contracts import (
    DocumentQualityReport,
    PreprocessingManifest,
    PreprocessingMode,
    PreprocessingRunStatus,
    ProcessedClinicalDocument,
)
from healthcare_language_ai.preprocessing.databricks import build_plan
from healthcare_language_ai.preprocessing.normalisation import (
    analytical_text,
    checksum_text,
    normalise_text,
)
from healthcare_language_ai.preprocessing.offsets import project_annotations
from healthcare_language_ai.preprocessing.quality import (
    document_quality_metrics,
    quality_status_counts,
)
from healthcare_language_ai.preprocessing.reconciliation import (
    build_reconciliation_report,
    count_by,
)
from healthcare_language_ai.preprocessing.sections import parse_sections
from healthcare_language_ai.preprocessing.sentences import segment_sentences
from healthcare_language_ai.preprocessing.serialisation import (
    DOCUMENT_COLUMNS,
    PROJECTION_COLUMNS,
    QUALITY_COLUMNS,
    SECTION_COLUMNS,
    SENTENCE_COLUMNS,
    write_csv,
    write_json_model,
    write_parquet,
)
from healthcare_language_ai.preprocessing.tokens import token_statistics
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_preprocessing_run_id(
    *,
    ingestion_manifest_checksum: str,
    contract_version: str,
    mode: PreprocessingMode,
    reference_timestamp: datetime,
    normalisation_version: str,
    section_parser_version: str,
    sentence_segmenter_version: str,
    tokeniser_version: str,
    quality_rules_version: str,
    write_csv_enabled: bool,
    write_parquet_enabled: bool,
) -> str:
    value = deterministic_id(
        {
            "ingestion_manifest_checksum": ingestion_manifest_checksum,
            "contract_version": contract_version,
            "mode": mode.value,
            "reference_timestamp": reference_timestamp.isoformat(),
            "normalisation_version": normalisation_version,
            "section_parser_version": section_parser_version,
            "sentence_segmenter_version": sentence_segmenter_version,
            "tokeniser_version": tokeniser_version,
            "quality_rules_version": quality_rules_version,
            "write_csv": write_csv_enabled,
            "write_parquet": write_parquet_enabled,
        },
        length=24,
    )
    return f"PRE-{value}"


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


def _load_annotations(path: Path) -> list[CanonicalDocumentAnnotation]:
    rows = _read_csv(path)
    annotations: list[CanonicalDocumentAnnotation] = []
    for row in rows:
        annotations.append(
            CanonicalDocumentAnnotation(
                annotation_id=row["annotation_id"],
                document_id=row["document_id"],
                annotation_type=row["annotation_type"],
                label=row["label"],
                value=row["value"],
                normalised_value=row["normalised_value"],
                start_offset=int(row["start_offset"]) if row["start_offset"] else None,
                end_offset=int(row["end_offset"]) if row["end_offset"] else None,
                annotation_source=row["annotation_source"],
                source_annotation_index=int(row["source_annotation_index"]),
                source_record_checksum=row["source_record_checksum"],
                ingestion_run_id=row["ingestion_run_id"],
            )
        )
    return annotations


def _ratio(text: str, predicate) -> float:  # type: ignore[no-untyped-def]
    return round(sum(1 for char in text if predicate(char)) / len(text), 6) if text else 0.0


def run_preprocessing(
    *,
    ingestion_dir: Path,
    output_root: Path,
    mode: PreprocessingMode,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: PreprocessingSettings,
) -> Path:
    """Run deterministic local preprocessing and return output directory."""
    failures = validate_ingestion_dir(ingestion_dir)
    if failures:
        msg = f"ingestion evidence failed validation: {failures[0]}"
        raise DataGovernanceError(msg)
    ingestion_manifest = load_ingestion_manifest(ingestion_dir)
    if not ingestion_manifest.synthetic_data_only or not ingestion_manifest.clinical_use_prohibited:
        msg = "source ingestion governance flags are unsafe"
        raise DataGovernanceError(msg)
    if ingestion_manifest.canonical_document_count > settings.maximum_documents_per_run:
        msg = "source document count exceeds configured preprocessing maximum"
        raise DataGovernanceError(msg)
    ingestion_manifest_checksum = sha256_file(ingestion_dir / "ingestion_manifest.json")
    run_id = derive_preprocessing_run_id(
        ingestion_manifest_checksum=ingestion_manifest_checksum,
        contract_version=settings.preprocessing_contract_version,
        mode=mode,
        reference_timestamp=reference_timestamp,
        normalisation_version=settings.normalisation_version,
        section_parser_version=settings.section_parser_version,
        sentence_segmenter_version=settings.sentence_segmenter_version,
        tokeniser_version=settings.tokeniser_version,
        quality_rules_version=settings.quality_rules_version,
        write_csv_enabled=settings.write_csv,
        write_parquet_enabled=settings.write_parquet,
    )
    output_dir = output_root / run_id
    _prepare_output_dir(output_dir, overwrite_policy)
    source_rows = _read_csv(ingestion_dir / "canonical_clinical_documents.csv")
    annotations = _load_annotations(ingestion_dir / "canonical_document_annotations.csv")
    annotations_by_doc: dict[str, list[CanonicalDocumentAnnotation]] = {}
    for annotation in annotations:
        annotations_by_doc.setdefault(annotation.document_id, []).append(annotation)

    processed_docs: list[ProcessedClinicalDocument] = []
    all_sections = []
    all_sentences = []
    quality_metrics = []
    all_projections = []
    source_text_by_doc: dict[str, str] = {}
    normalised_text_by_doc: dict[str, str] = {}
    for row in sorted(source_rows, key=lambda item: item["document_id"]):
        source_text = row["document_text"]
        normalised, _transformations = normalise_text(
            source_text,
            unicode_form=settings.unicode_normalisation_form,
            tab_width=settings.tab_width,
            collapse_spaces=settings.collapse_repeated_spaces,
            preserve_final_newline=settings.preserve_final_newline,
            version=settings.normalisation_version,
        )
        source_text_by_doc[row["document_id"]] = source_text
        normalised_text_by_doc[row["document_id"]] = normalised
        sections = parse_sections(normalised, document_id=row["document_id"], run_id=run_id)
        sentences = segment_sentences(text=normalised, sections=sections, run_id=run_id)
        stats = token_statistics(normalised)
        projections = project_annotations(
            annotations=annotations_by_doc.get(row["document_id"], []),
            source_text_by_document=source_text_by_doc,
            normalised_text_by_document=normalised_text_by_doc,
            run_id=run_id,
        )
        projection_counts = count_by([item.projection_status for item in projections])
        doc_quality = document_quality_metrics(
            document_id=row["document_id"],
            text=normalised,
            section_count=len(sections),
            sentence_lengths=[len(item.sentence_text) for item in sentences],
            projection_status_counts=projection_counts,
            minimum_document_length=settings.minimum_document_length,
            maximum_sentence_length=settings.maximum_sentence_length,
            run_id=run_id,
        )
        processed_docs.append(
            ProcessedClinicalDocument(
                document_id=row["document_id"],
                synthetic_subject_id=row["synthetic_subject_id"],
                synthetic_encounter_id=row["synthetic_encounter_id"],
                document_type=row["document_type"],
                source_text=source_text,
                normalised_text=normalised,
                analytical_text=analytical_text(normalised)
                if mode is PreprocessingMode.ANALYTICAL
                else None,
                preprocessing_mode=mode,
                source_character_count=len(source_text),
                normalised_character_count=len(normalised),
                sentence_count=len(sentences),
                section_count=len(sections),
                token_count=int(stats["token_count"]),
                unique_token_count=int(stats["unique_token_count"]),
                line_count=normalised.count("\n"),
                empty_line_count=sum(not line.strip() for line in normalised.split("\n")),
                uppercase_ratio=_ratio(normalised, str.isupper),
                digit_ratio=_ratio(normalised, str.isdigit),
                whitespace_ratio=_ratio(normalised, str.isspace),
                contains_replacement_character="\ufffd" in normalised,
                source_record_checksum=row["source_record_checksum"],
                normalised_text_checksum=checksum_text(normalised),
                analytical_text_checksum=checksum_text(analytical_text(normalised))
                if mode is PreprocessingMode.ANALYTICAL
                else None,
                ingestion_run_id=row["ingestion_run_id"],
                preprocessing_run_id=run_id,
                preprocessed_at=reference_timestamp,
                normalisation_version=settings.normalisation_version,
                section_parser_version=settings.section_parser_version,
                sentence_segmenter_version=settings.sentence_segmenter_version,
                tokeniser_version=settings.tokeniser_version,
                quality_rules_version=settings.quality_rules_version,
            )
        )
        all_sections.extend(sections)
        all_sentences.extend(sentences)
        all_projections.extend(projections)
        quality_metrics.extend(doc_quality)

    all_sections.sort(key=lambda item: (item.document_id, item.section_index))
    all_sentences.sort(key=lambda item: (item.document_id, item.document_sentence_index))
    all_projections.sort(key=lambda item: item.projection_id)
    quality_metrics.sort(key=lambda item: (item.document_id, item.check_name))
    if settings.write_csv:
        write_csv(output_dir / "processed_documents.csv", processed_docs, DOCUMENT_COLUMNS)
        write_csv(output_dir / "processed_sections.csv", all_sections, SECTION_COLUMNS)
        write_csv(output_dir / "processed_sentences.csv", all_sentences, SENTENCE_COLUMNS)
        write_csv(output_dir / "projected_annotations.csv", all_projections, PROJECTION_COLUMNS)
        write_csv(output_dir / "document_quality_report.csv", quality_metrics, QUALITY_COLUMNS)
    if settings.write_parquet:
        compression = "zstd"
        write_parquet(
            output_dir / "processed_documents.parquet",
            processed_docs,
            DOCUMENT_COLUMNS,
            compression=compression,
        )
        write_parquet(
            output_dir / "processed_sections.parquet",
            all_sections,
            SECTION_COLUMNS,
            compression=compression,
        )
        write_parquet(
            output_dir / "processed_sentences.parquet",
            all_sentences,
            SENTENCE_COLUMNS,
            compression=compression,
        )
        write_parquet(
            output_dir / "projected_annotations.parquet",
            all_projections,
            PROJECTION_COLUMNS,
            compression=compression,
        )

    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "preprocessing_manifest.json"
    }
    plan = build_plan(
        run_id=run_id,
        source_files=sorted(output_checksums),
        checksums=output_checksums,
        document_count=len(processed_docs),
        sentence_count=len(all_sentences),
        quality_status="passed",
    )
    write_json_model(output_dir / "databricks_pipeline_plan.json", plan)
    output_checksums["databricks_pipeline_plan.json"] = sha256_file(
        output_dir / "databricks_pipeline_plan.json"
    )
    quality_report = DocumentQualityReport(
        quality_schema_version="1.0.0",
        preprocessing_run_id=run_id,
        overall_status="failed"
        if any(item.status == "failed" for item in quality_metrics)
        else "warning"
        if any(item.status == "warning" for item in quality_metrics)
        else "passed",
        metrics=quality_metrics,
    )
    write_json_model(output_dir / "document_quality_report.json", quality_report)
    output_checksums["document_quality_report.json"] = sha256_file(
        output_dir / "document_quality_report.json"
    )
    reconciliation = build_reconciliation_report(
        run_id=run_id,
        source_document_count=ingestion_manifest.canonical_document_count,
        source_annotation_count=ingestion_manifest.canonical_annotation_count,
        documents=processed_docs,
        sections=all_sections,
        sentences=all_sentences,
        projections=all_projections,
        output_checksum_status=True,
        databricks_plan_valid=True,
    )
    write_json_model(output_dir / "preprocessing_reconciliation.json", reconciliation)
    output_checksums["preprocessing_reconciliation.json"] = sha256_file(
        output_dir / "preprocessing_reconciliation.json"
    )
    projection_counts = count_by([item.projection_status for item in all_projections])
    manifest = PreprocessingManifest(
        manifest_schema_version="1.0.0",
        preprocessing_contract_version=settings.preprocessing_contract_version,
        preprocessing_run_id=run_id,
        preprocessing_mode=mode,
        run_status=PreprocessingRunStatus.COMPLETED_WITH_WARNINGS
        if quality_report.overall_status == "warning"
        else PreprocessingRunStatus.COMPLETED,
        source_ingestion_run_id=ingestion_manifest.ingestion_run_id,
        source_ingestion_manifest_checksum=ingestion_manifest_checksum,
        source_document_count=ingestion_manifest.canonical_document_count,
        source_annotation_count=ingestion_manifest.canonical_annotation_count,
        processed_document_count=len(processed_docs),
        section_count=len(all_sections),
        sentence_count=len(all_sentences),
        projected_annotation_count=len(all_projections) - projection_counts.get("unresolved", 0),
        unresolved_annotation_count=projection_counts.get("unresolved", 0),
        warning_count=sum(item.status == "warning" for item in quality_metrics),
        failure_count=sum(item.status == "failed" for item in quality_metrics),
        total_lexical_token_count=sum(item.token_count for item in processed_docs),
        normalisation_version=settings.normalisation_version,
        section_parser_version=settings.section_parser_version,
        sentence_segmenter_version=settings.sentence_segmenter_version,
        tokeniser_version=settings.tokeniser_version,
        quality_rules_version=settings.quality_rules_version,
        databricks_contract_version=settings.databricks_contract_version,
        reference_timestamp=reference_timestamp,
        writer_versions={"pyarrow": pyarrow.__version__, "csv": "python-stdlib"},
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        document_type_counts=count_by([item.document_type for item in processed_docs]),
        section_label_counts=count_by([item.normalised_section_label for item in all_sections]),
        quality_status_counts=quality_status_counts(quality_metrics),
        annotation_projection_status_counts=projection_counts,
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status=reconciliation.overall_status,
    )
    write_json_model(output_dir / "preprocessing_manifest.json", manifest)
    readme = (
        "# Local Preprocessing Evidence\n\n"
        f"Run ID: {run_id}\n"
        "No Databricks connection was attempted.\n"
    )
    (output_dir / "README.md").write_text(
        readme,
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def load_preprocessing_manifest(preprocessing_dir: Path) -> PreprocessingManifest:
    return PreprocessingManifest.model_validate(
        read_json(preprocessing_dir / "preprocessing_manifest.json")
    )
