"""Deterministic synthetic clinical-document generation and dataset writing."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

from healthcare_language_ai.domain.enums import ClinicalDocumentType
from healthcare_language_ai.synthetic.annotations import span_annotation
from healthcare_language_ai.synthetic.manifest import build_manifest, sha256_file
from healthcare_language_ai.synthetic.models import (
    DocumentAnnotation,
    SyntheticClinicalDocument,
    SyntheticDataset,
    SyntheticDocumentMetadata,
    SyntheticDocumentRecord,
)
from healthcare_language_ai.synthetic.quality import build_quality_report
from healthcare_language_ai.synthetic.serialization import write_json, write_jsonl
from healthcare_language_ai.synthetic.templates import TEMPLATE_VERSION, render_template
from healthcare_language_ai.synthetic.validation import validate_records
from healthcare_language_ai.synthetic.vocabularies import (
    ADMINISTRATIVE_PRIORITIES,
    BODY_SITES,
    ENCOUNTER_CONTEXTS,
    FOLLOW_UP_PLACEHOLDERS,
    INVESTIGATIONS,
    OBSERVATIONS,
    PRESENTING_CONCERNS,
    REPORT_DESCRIPTORS,
    SPECIALTIES,
    VOCABULARY_VERSION,
    WORKFLOW_STATUSES,
)

GENERATOR_VERSION = "1.0.0"


def synthetic_subject_id(seed: int, record_index: int, document_type: ClinicalDocumentType) -> str:
    value = abs(hashless_int(seed, record_index, document_type.value, "subject")) % 999_999 + 1
    return f"SYN-SUBJ-{value:06d}"


def synthetic_encounter_id(
    seed: int, record_index: int, document_type: ClinicalDocumentType
) -> str:
    value = abs(hashless_int(seed, record_index, document_type.value, "encounter")) % 999_999 + 1
    return f"SYN-ENC-{value:06d}"


def synthetic_document_id(seed: int, record_index: int, document_type: ClinicalDocumentType) -> str:
    value = abs(hashless_int(seed, record_index, document_type.value, "document")) % 999_999 + 1
    return f"SYN-DOC-{value:06d}"


def synthetic_run_id(seed: int, count: int, document_types: list[ClinicalDocumentType]) -> str:
    joined = ",".join(document_type.value for document_type in document_types)
    value = abs(hashless_int(seed, count, joined, GENERATOR_VERSION)) % 999_999_999
    return f"SYN-RUN-{value:09d}"


def hashless_int(*parts: object) -> int:
    """Stable non-cryptographic integer for readable deterministic IDs."""
    from healthcare_language_ai.utils.identifiers import deterministic_id

    return int(deterministic_id([str(part) for part in parts], length=16), 16)


def _choice(rng: random.Random, values: list[str]) -> str:
    return values[rng.randrange(0, len(values))]


def _document_type_for_index(
    index: int, document_types: list[ClinicalDocumentType]
) -> ClinicalDocumentType:
    return document_types[(index - 1) % len(document_types)]


def generate_dataset(
    *,
    count: int,
    seed: int,
    document_types: list[ClinicalDocumentType],
    reference_timestamp: datetime,
    max_document_text_length: int,
    generator_version: str = GENERATOR_VERSION,
    template_version: str = TEMPLATE_VERSION,
    vocabulary_version: str = VOCABULARY_VERSION,
) -> SyntheticDataset:
    """Generate deterministic synthetic document records."""
    records: list[SyntheticDocumentRecord] = []
    for index in range(1, count + 1):
        document_type = _document_type_for_index(index, document_types)
        rng = random.Random(f"{seed}:{index}:{document_type.value}:{generator_version}")
        encounter_started = reference_timestamp + timedelta(hours=index * 3)
        encounter_ended = encounter_started + timedelta(hours=2)
        created_at = encounter_ended + timedelta(minutes=15)
        subject_id = synthetic_subject_id(seed, index, document_type)
        encounter_id = synthetic_encounter_id(seed, index, document_type)
        values = {
            "synthetic_subject_id": subject_id,
            "synthetic_encounter_id": encounter_id,
            "seed": str(seed),
            "record_index": str(index),
            "presenting_concern": _choice(rng, PRESENTING_CONCERNS),
            "observation": _choice(rng, OBSERVATIONS),
            "body_site": _choice(rng, BODY_SITES),
            "investigation": _choice(rng, INVESTIGATIONS),
            "encounter_context": _choice(rng, ENCOUNTER_CONTEXTS),
            "workflow_status": _choice(rng, WORKFLOW_STATUSES),
            "specialty": _choice(rng, SPECIALTIES),
            "administrative_priority": _choice(rng, ADMINISTRATIVE_PRIORITIES),
            "descriptor": _choice(rng, REPORT_DESCRIPTORS),
            "follow_up": _choice(rng, FOLLOW_UP_PLACEHOLDERS),
        }
        template = render_template(document_type, values)
        if len(template.text) > max_document_text_length:
            msg = "generated text exceeded configured maximum length"
            raise ValueError(msg)
        metadata = SyntheticDocumentMetadata(
            synthetic_subject_id=subject_id,
            synthetic_encounter_id=encounter_id,
            encounter_context=values["encounter_context"],
            specialty=values["specialty"],
            body_site=values["body_site"],
            presenting_concern=values["presenting_concern"],
            investigation=values["investigation"],
            administrative_priority=values["administrative_priority"],
            workflow_status=values["workflow_status"],
        )
        document = SyntheticClinicalDocument(
            document_id=synthetic_document_id(seed, index, document_type),
            document_type=document_type,
            text=template.text,
            created_at=created_at,
            encounter_started_at=encounter_started,
            encounter_ended_at=encounter_ended,
            metadata=metadata,
            generator_version=generator_version,
            template_name=template.template_name,
            template_version=template_version,
            vocabulary_version=vocabulary_version,
            seed=seed,
            record_index=index,
        )
        annotation = DocumentAnnotation(
            document_id=document.document_id,
            synthetic_subject_id=subject_id,
            synthetic_encounter_id=encounter_id,
            document_type=document_type,
            entities=[
                span_annotation(template.text, label=label, value=value)
                for label, value in sorted(template.span_values.items())
            ],
            document_level=template.document_level,
        )
        records.append(SyntheticDocumentRecord(document=document, annotation=annotation))
    checks = validate_records(records, max_document_text_length=max_document_text_length)
    report = build_quality_report(records, checks)
    if report.validation_status == "failed":
        failures = "; ".join(check.message for check in checks if check.status == "failed")
        raise ValueError(f"generated dataset failed validation: {failures}")
    return SyntheticDataset(records=records, quality_report=report)


def write_dataset(
    *,
    dataset: SyntheticDataset,
    output_dir: Path,
    seed: int,
    reference_timestamp: datetime,
    generator_version: str = GENERATOR_VERSION,
    template_version: str = TEMPLATE_VERSION,
    vocabulary_version: str = VOCABULARY_VERSION,
) -> SyntheticDataset:
    """Write canonical dataset files and return a dataset with manifest."""
    expected_files = {
        "clinical_documents.jsonl",
        "document_annotations.jsonl",
        "dataset_manifest.json",
        "data_quality_report.json",
        "README.md",
    }
    if output_dir.exists():
        unexpected = sorted(
            path.name for path in output_dir.iterdir() if path.name not in expected_files
        )
        if unexpected:
            msg = f"output directory contains non-generated files: {unexpected}"
            raise ValueError(msg)
    output_dir.mkdir(parents=True, exist_ok=True)
    document_path = output_dir / "clinical_documents.jsonl"
    annotation_path = output_dir / "document_annotations.jsonl"
    write_jsonl(document_path, [record.document for record in dataset.records])
    write_jsonl(annotation_path, [record.annotation for record in dataset.records])
    checksums = {
        document_path.name: sha256_file(document_path),
        annotation_path.name: sha256_file(annotation_path),
    }
    manifest = build_manifest(
        records=dataset.records,
        seed=seed,
        reference_timestamp=reference_timestamp,
        generator_version=generator_version,
        template_version=template_version,
        vocabulary_version=vocabulary_version,
        file_checksums=checksums,
    )
    dataset.manifest = manifest
    if dataset.quality_report is None:
        dataset.quality_report = build_quality_report(dataset.records, [])
    write_json(output_dir / "dataset_manifest.json", manifest)
    write_json(output_dir / "data_quality_report.json", dataset.quality_report)
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Synthetic Clinical Document Dataset",
                "",
                "This deterministic fixture contains synthetic data only.",
                "It is for educational portfolio testing and is not for clinical use.",
                "",
                f"Record count: {len(dataset.records)}",
                f"Seed: {seed}",
                f"Reference timestamp: {reference_timestamp.isoformat()}",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return dataset
