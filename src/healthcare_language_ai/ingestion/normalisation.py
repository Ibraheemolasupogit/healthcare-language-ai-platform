"""Normalise Milestone 2 source records into canonical ingestion rows."""

from __future__ import annotations

from datetime import datetime

from healthcare_language_ai.ingestion.contracts import (
    CanonicalClinicalDocument,
    CanonicalDocumentAnnotation,
)
from healthcare_language_ai.synthetic.manifest import DATASET_NAME, DATASET_VERSION
from healthcare_language_ai.synthetic.models import DocumentAnnotation, SyntheticClinicalDocument
from healthcare_language_ai.synthetic.serialization import canonical_json_line
from healthcare_language_ai.utils.identifiers import deterministic_id


def source_record_checksum(document: SyntheticClinicalDocument) -> str:
    return deterministic_id(document.model_dump(mode="json"), length=64)


def canonical_document(
    *,
    document: SyntheticClinicalDocument,
    source_line_number: int,
    ingestion_run_id: str,
    ingested_at: datetime,
    source_reference_timestamp: datetime,
) -> CanonicalClinicalDocument:
    checksum = source_record_checksum(document)
    return CanonicalClinicalDocument(
        document_id=document.document_id,
        synthetic_subject_id=document.metadata.synthetic_subject_id,
        synthetic_encounter_id=document.metadata.synthetic_encounter_id,
        document_type=document.document_type.value,
        source_system=document.source_system,
        data_classification=document.data_classification.value,
        document_text=document.text,
        document_created_at=document.created_at,
        encounter_started_at=document.encounter_started_at,
        encounter_ended_at=document.encounter_ended_at,
        generator_version=document.generator_version,
        template_name=document.template_name,
        template_version=document.template_version,
        vocabulary_version=document.vocabulary_version,
        source_dataset_name=DATASET_NAME,
        source_dataset_version=DATASET_VERSION,
        source_seed=document.seed,
        source_reference_timestamp=source_reference_timestamp,
        source_record_index=document.record_index,
        source_file="clinical_documents.jsonl",
        source_line_number=source_line_number,
        source_record_checksum=checksum,
        ingestion_run_id=ingestion_run_id,
        ingested_at=ingested_at,
    )


def canonical_annotations(
    *,
    annotation: DocumentAnnotation,
    document: SyntheticClinicalDocument,
    ingestion_run_id: str,
) -> list[CanonicalDocumentAnnotation]:
    checksum = source_record_checksum(document)
    rows: list[CanonicalDocumentAnnotation] = []
    for index, entity in enumerate(annotation.entities, start=1):
        annotation_id = deterministic_id(
            [ingestion_run_id, annotation.document_id, "span", index, entity.label, entity.value],
            prefix="ANN",
            length=24,
        )
        rows.append(
            CanonicalDocumentAnnotation(
                annotation_id=annotation_id,
                document_id=annotation.document_id,
                annotation_type="span",
                label=entity.label,
                value=entity.value,
                normalised_value=entity.normalised_value,
                start_offset=entity.start,
                end_offset=entity.end,
                annotation_source=entity.source,
                source_annotation_index=index,
                source_record_checksum=checksum,
                ingestion_run_id=ingestion_run_id,
            )
        )
    offset = len(rows)
    for index, (label, value) in enumerate(sorted(annotation.document_level.items()), start=1):
        value_text = str(value)
        annotation_id = deterministic_id(
            [ingestion_run_id, annotation.document_id, "document_level", label, value_text],
            prefix="ANN",
            length=24,
        )
        rows.append(
            CanonicalDocumentAnnotation(
                annotation_id=annotation_id,
                document_id=annotation.document_id,
                annotation_type="document_level",
                label=label,
                value=value_text,
                normalised_value=value_text,
                start_offset=None,
                end_offset=None,
                annotation_source="document_level",
                source_annotation_index=offset + index,
                source_record_checksum=checksum,
                ingestion_run_id=ingestion_run_id,
            )
        )
    return rows


def canonical_row_checksum(row: CanonicalClinicalDocument | CanonicalDocumentAnnotation) -> str:
    return deterministic_id(canonical_json_line(row), length=64)
