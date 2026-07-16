"""Deterministic local ingestion pipeline."""

from __future__ import annotations

import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

import pyarrow

from healthcare_language_ai.config import IngestionSettings
from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.ingestion.contracts import (
    CanonicalClinicalDocument,
    CanonicalDocumentAnnotation,
    IngestionManifest,
    IngestionMode,
    IngestionRunStatus,
    OverwritePolicy,
    QuarantineRecord,
)
from healthcare_language_ai.ingestion.discovery import discover_source
from healthcare_language_ai.ingestion.loader import (
    load_source_annotations,
    load_source_documents,
    validate_source_dataset,
)
from healthcare_language_ai.ingestion.normalisation import canonical_annotations, canonical_document
from healthcare_language_ai.ingestion.reconciliation import build_reconciliation_report
from healthcare_language_ai.ingestion.serialisation import (
    ANNOTATION_COLUMNS,
    DOCUMENT_COLUMNS,
    write_csv,
    write_json_model,
    write_parquet,
)
from healthcare_language_ai.ingestion.snowflake import build_load_plan
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.models import DocumentAnnotation, SyntheticDocumentRecord
from healthcare_language_ai.synthetic.serialization import read_json, write_jsonl
from healthcare_language_ai.synthetic.validation import validate_records
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_ingestion_run_id(
    *,
    source_manifest_checksum: str,
    contract_version: str,
    mode: IngestionMode,
    reference_timestamp: datetime,
    write_csv_enabled: bool,
    write_parquet_enabled: bool,
) -> str:
    value = deterministic_id(
        {
            "source_manifest_checksum": source_manifest_checksum,
            "contract_version": contract_version,
            "mode": mode.value,
            "reference_timestamp": reference_timestamp.isoformat(),
            "write_csv": write_csv_enabled,
            "write_parquet": write_parquet_enabled,
        },
        length=24,
    )
    return f"ING-{value}"


def _prepare_output_dir(output_dir: Path, policy: OverwritePolicy) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if policy is OverwritePolicy.FAIL_IF_EXISTS:
        msg = f"output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    if policy is OverwritePolicy.FORCE_REPLACE:
        shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        return
    manifest = output_dir / "ingestion_manifest.json"
    if not manifest.exists():
        msg = "replace_identical requires an existing ingestion manifest"
        raise FileExistsError(msg)
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _source_annotation_count(annotations: list[DocumentAnnotation]) -> int:
    return sum(len(item.entities) + len(item.document_level) for item in annotations)


def _quarantine_invalid_records(
    records: list[SyntheticDocumentRecord],
    *,
    max_document_text_length: int,
    timestamp: datetime,
) -> tuple[list[SyntheticDocumentRecord], list[QuarantineRecord]]:
    checks = validate_records(records, max_document_text_length=max_document_text_length)
    failed_by_document: set[str] = set()
    for check in checks:
        if check.status == "failed" and check.name.startswith("SYN-DOC-"):
            failed_by_document.add(check.name.split(":", 1)[0])
    valid = [record for record in records if record.document.document_id not in failed_by_document]
    quarantine = [
        QuarantineRecord(
            source_file="clinical_documents.jsonl",
            source_line_number=record.document.record_index,
            record_identifier=record.document.document_id,
            error_code="SOURCE_RECORD_VALIDATION_FAILED",
            error_category="data_quality",
            sanitised_error_message="source record failed validation; clinical text omitted",
            payload_checksum=deterministic_id(record.document.model_dump(mode="json"), length=64),
            quarantine_timestamp=timestamp,
        )
        for record in records
        if record.document.document_id in failed_by_document
    ]
    return valid, quarantine


def run_ingestion(
    *,
    source_dir: Path,
    output_root: Path,
    mode: IngestionMode,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: IngestionSettings,
    max_document_text_length: int,
) -> Path:
    """Run deterministic ingestion and return the output directory."""
    source = discover_source(source_dir, follow_symlinks=settings.follow_symlinks)
    source_manifest = validate_source_dataset(
        source.source_dir, max_document_text_length=max_document_text_length
    )
    run_id = derive_ingestion_run_id(
        source_manifest_checksum=source.source_manifest_checksum,
        contract_version=settings.ingestion_contract_version,
        mode=mode,
        reference_timestamp=reference_timestamp,
        write_csv_enabled=settings.write_csv,
        write_parquet_enabled=settings.write_parquet,
    )
    output_dir = output_root / run_id
    _prepare_output_dir(output_dir, overwrite_policy)

    source_documents = load_source_documents(source.source_dir)
    source_annotations = load_source_annotations(source.source_dir)
    if len(source_documents) > settings.maximum_source_records:
        msg = "source record count exceeds configured maximum"
        raise DataGovernanceError(msg)
    annotations_by_document = {item.document_id: item for item in source_annotations}
    source_records = [
        SyntheticDocumentRecord(
            document=document, annotation=annotations_by_document[document.document_id]
        )
        for document in source_documents
    ]
    quarantine_records: list[QuarantineRecord] = []
    if mode is IngestionMode.QUARANTINE:
        source_records, quarantine_records = _quarantine_invalid_records(
            source_records,
            max_document_text_length=max_document_text_length,
            timestamp=reference_timestamp,
        )
    else:
        checks = validate_records(source_records, max_document_text_length=max_document_text_length)
        if any(check.status == "failed" for check in checks):
            msg = "strict ingestion failed source record validation"
            raise DataGovernanceError(msg)

    canonical_documents: list[CanonicalClinicalDocument] = []
    canonical_annotations_rows: list[CanonicalDocumentAnnotation] = []
    for line_number, record in enumerate(source_records, start=1):
        doc_row = canonical_document(
            document=record.document,
            source_line_number=line_number,
            ingestion_run_id=run_id,
            ingested_at=reference_timestamp,
            source_reference_timestamp=source_manifest.reference_timestamp,
        )
        canonical_documents.append(doc_row)
        canonical_annotations_rows.extend(
            canonical_annotations(
                annotation=record.annotation,
                document=record.document,
                ingestion_run_id=run_id,
            )
        )
    canonical_documents.sort(key=lambda item: item.document_id)
    canonical_annotations_rows.sort(key=lambda item: item.annotation_id)
    reconciliation = build_reconciliation_report(
        ingestion_run_id=run_id,
        source_document_count=len(source_records),
        source_annotation_count=_source_annotation_count(
            [record.annotation for record in source_records]
        ),
        documents=canonical_documents,
        annotations=canonical_annotations_rows,
        quarantine_count=len(quarantine_records),
        source_document_type_counts=dict(
            sorted(
                Counter(record.document.document_type.value for record in source_records).items()
            )
        ),
        source_annotation_label_counts=dict(
            sorted(Counter(row.label for row in canonical_annotations_rows).items())
        ),
    )
    run_status = (
        IngestionRunStatus.COMPLETED_WITH_QUARANTINE
        if quarantine_records
        else IngestionRunStatus.COMPLETED
    )

    if settings.write_csv:
        write_csv(
            output_dir / "canonical_clinical_documents.csv",
            canonical_documents,
            DOCUMENT_COLUMNS,
            null_value=settings.csv_null_value,
        )
        write_csv(
            output_dir / "canonical_document_annotations.csv",
            canonical_annotations_rows,
            ANNOTATION_COLUMNS,
            null_value=settings.csv_null_value,
        )
    if settings.write_parquet:
        write_parquet(
            output_dir / "canonical_clinical_documents.parquet",
            canonical_documents,
            DOCUMENT_COLUMNS,
            compression=settings.parquet_compression,
        )
        write_parquet(
            output_dir / "canonical_document_annotations.parquet",
            canonical_annotations_rows,
            ANNOTATION_COLUMNS,
            compression=settings.parquet_compression,
        )
    if quarantine_records:
        quarantine_dir = output_dir / "quarantine"
        quarantine_dir.mkdir()
        write_jsonl(quarantine_dir / "quarantine_records.jsonl", quarantine_records)
        write_json_model(
            quarantine_dir / "quarantine_summary.json",
            {
                "quarantine_count": len(quarantine_records),
                "contains_full_clinical_text": False,
                "payload_checksums": [record.payload_checksum for record in quarantine_records],
            },
        )

    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "ingestion_manifest.json"
    }
    source_checksums = {file.file_name: file.sha256 for file in source.files}
    plan = build_load_plan(
        output_dir=output_dir,
        target_database=settings.snowflake_target_database,
        raw_schema=settings.snowflake_raw_schema,
        staging_schema=settings.snowflake_staging_schema,
        governance_schema=settings.snowflake_governance_schema,
        snowflake_contract_version=settings.snowflake_contract_version,
        checksums=output_checksums,
        document_count=len(canonical_documents),
        annotation_count=len(canonical_annotations_rows),
    )
    write_json_model(output_dir / "snowflake_load_plan.json", plan)
    output_checksums["snowflake_load_plan.json"] = sha256_file(
        output_dir / "snowflake_load_plan.json"
    )
    write_json_model(output_dir / "reconciliation_report.json", reconciliation)
    output_checksums["reconciliation_report.json"] = sha256_file(
        output_dir / "reconciliation_report.json"
    )
    manifest = IngestionManifest(
        manifest_schema_version="1.0.0",
        ingestion_contract_version=settings.ingestion_contract_version,
        ingestion_run_id=run_id,
        ingestion_mode=mode,
        run_status=run_status,
        source_dataset_name=source_manifest.dataset_name,
        source_dataset_version=source_manifest.dataset_version,
        source_manifest_checksum=source.source_manifest_checksum,
        source_file_checksums=source_checksums,
        source_record_count=source_manifest.record_count,
        source_annotation_count=_source_annotation_count(source_annotations),
        canonical_document_count=len(canonical_documents),
        canonical_annotation_count=len(canonical_annotations_rows),
        quarantine_count=len(quarantine_records),
        duplicate_count=0,
        orphan_annotation_count=0,
        generator_version=source_manifest.generator_version,
        template_version=source_manifest.template_version,
        vocabulary_version=source_manifest.vocabulary_version,
        reference_timestamp=reference_timestamp,
        writer_versions={"pyarrow": pyarrow.__version__, "csv": "python-stdlib"},
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        snowflake_contract_version=settings.snowflake_contract_version,
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        document_type_counts=dict(Counter(row.document_type for row in canonical_documents)),
        annotation_label_counts=dict(Counter(row.label for row in canonical_annotations_rows)),
        reconciliation_status=reconciliation.overall_status,
    )
    write_json_model(output_dir / "ingestion_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Local Ingestion Evidence",
                "",
                "Deterministic local ingestion output for synthetic data only.",
                "No Snowflake connection was attempted.",
                "",
                f"Ingestion run ID: {run_id}",
                f"Run status: {run_status.value}",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def load_ingestion_manifest(ingestion_dir: Path) -> IngestionManifest:
    return IngestionManifest.model_validate(read_json(ingestion_dir / "ingestion_manifest.json"))
