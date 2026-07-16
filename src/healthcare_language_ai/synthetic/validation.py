"""Data-quality, privacy, governance, and checksum validation."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from healthcare_language_ai.domain.enums import ClinicalDocumentType, DataClassification
from healthcare_language_ai.synthetic.manifest import (
    annotation_label_counts,
    document_type_counts,
    sha256_file,
)
from healthcare_language_ai.synthetic.models import (
    DatasetManifest,
    DocumentAnnotation,
    SyntheticClinicalDocument,
    SyntheticDocumentRecord,
    ValidationCheck,
)
from healthcare_language_ai.synthetic.serialization import read_json, read_jsonl

SYNTHETIC_ID_PATTERNS = {
    "document_id": re.compile(r"^SYN-DOC-\d{6}$"),
    "subject_id": re.compile(r"^SYN-SUBJ-\d{6}$"),
    "encounter_id": re.compile(r"^SYN-ENC-\d{6}$"),
}

SUSPICIOUS_PATTERNS = {
    "nhs_number_like": re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{4}\b"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "uk_phone": re.compile(r"\b(?:\+44\s?7\d{3}|07\d{3})\s?\d{3}\s?\d{3}\b"),
    "postcode": re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b", re.IGNORECASE),
    "url": re.compile(r"https?://|www\.", re.IGNORECASE),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "credit_card_like": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "national_insurance_like": re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b", re.IGNORECASE),
    "long_unapproved_number": re.compile(r"\b(?!SYN-)\d{7,}\b"),
}

PROHIBITED_RECOMMENDATION_PHRASES = [
    "you should take",
    "start taking",
    "stop taking",
    "recommended treatment",
    "medical advice",
    "diagnosis confirmed",
    "urgent treatment required",
]

PROHIBITED_STRUCTURED_FIELDS = {"name", "patient_name", "address", "phone", "email"}


def _check(name: str, passed: bool, message: str) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        status="passed" if passed else "failed",
        message=message,
        severity="info" if passed else "error",
    )


def validate_records(
    records: list[SyntheticDocumentRecord], *, max_document_text_length: int
) -> list[ValidationCheck]:
    """Validate in-memory synthetic records."""
    checks: list[ValidationCheck] = []
    document_ids = [record.document.document_id for record in records]
    encounter_ids = [record.document.metadata.synthetic_encounter_id for record in records]
    checks.append(_check("record_count_positive", len(records) > 0, "record count is positive"))
    checks.append(
        _check(
            "unique_document_ids",
            len(set(document_ids)) == len(document_ids),
            "document IDs are unique",
        )
    )
    checks.append(
        _check(
            "unique_encounter_ids",
            len(set(encounter_ids)) == len(encounter_ids),
            "encounter IDs are unique",
        )
    )
    for record in records:
        document = record.document
        annotation = record.annotation
        prefix_ok = (
            SYNTHETIC_ID_PATTERNS["document_id"].match(document.document_id)
            and SYNTHETIC_ID_PATTERNS["subject_id"].match(document.metadata.synthetic_subject_id)
            and SYNTHETIC_ID_PATTERNS["encounter_id"].match(
                document.metadata.synthetic_encounter_id
            )
        )
        checks.append(
            _check(
                f"{document.document_id}:synthetic_prefixes",
                bool(prefix_ok),
                "synthetic ID prefixes are approved",
            )
        )
        checks.append(
            _check(
                f"{document.document_id}:synthetic_classification",
                document.data_classification is DataClassification.SYNTHETIC,
                "classification is synthetic",
            )
        )
        checks.append(
            _check(
                f"{document.document_id}:text_present",
                bool(document.text.strip()),
                "document text is non-empty",
            )
        )
        checks.append(
            _check(
                f"{document.document_id}:text_length",
                len(document.text) <= max_document_text_length,
                "document text length is within limit",
            )
        )
        checks.append(
            _check(
                f"{document.document_id}:chronology",
                document.encounter_started_at <= document.encounter_ended_at <= document.created_at,
                "timestamps are chronological",
            )
        )
        checks.extend(_validate_annotation_offsets(document, annotation))
        checks.extend(_validate_governance_patterns(document))
        checks.extend(_validate_structured_schema(document, annotation))
    return checks


def _validate_annotation_offsets(
    document: SyntheticClinicalDocument, annotation: DocumentAnnotation
) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    for entity in annotation.entities:
        valid = (
            entity.end <= len(document.text)
            and document.text[entity.start : entity.end] == entity.value
        )
        checks.append(
            _check(
                f"{document.document_id}:annotation:{entity.label}",
                valid,
                "annotation offset matches text span",
            )
        )
    return checks


def _validate_governance_patterns(document: SyntheticClinicalDocument) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    for name, pattern in SUSPICIOUS_PATTERNS.items():
        checks.append(
            _check(
                f"{document.document_id}:privacy:{name}",
                pattern.search(document.text) is None,
                f"no {name} pattern found",
            )
        )
    lower_text = document.text.lower()
    for phrase in PROHIBITED_RECOMMENDATION_PHRASES:
        checks.append(
            _check(
                f"{document.document_id}:clinical_safety:{phrase}",
                phrase not in lower_text,
                f"prohibited phrase absent: {phrase}",
            )
        )
    return checks


def _validate_structured_schema(
    document: SyntheticClinicalDocument, annotation: DocumentAnnotation
) -> list[ValidationCheck]:
    payload = {
        **document.model_dump(mode="json"),
        **annotation.model_dump(mode="json"),
    }
    present = PROHIBITED_STRUCTURED_FIELDS.intersection(payload)
    return [
        _check(
            f"{document.document_id}:no_real_person_fields",
            not present,
            "no real-person structured fields exist",
        )
    ]


def load_dataset(dataset_dir: Path) -> tuple[list[SyntheticDocumentRecord], DatasetManifest]:
    documents = [
        SyntheticClinicalDocument.model_validate(row)
        for row in read_jsonl(dataset_dir / "clinical_documents.jsonl")
    ]
    annotations = [
        DocumentAnnotation.model_validate(row)
        for row in read_jsonl(dataset_dir / "document_annotations.jsonl")
    ]
    annotation_by_id = {annotation.document_id: annotation for annotation in annotations}
    records = [
        SyntheticDocumentRecord(
            document=document, annotation=annotation_by_id[document.document_id]
        )
        for document in documents
    ]
    manifest = DatasetManifest.model_validate(read_json(dataset_dir / "dataset_manifest.json"))
    return records, manifest


def validate_dataset_dir(
    dataset_dir: Path, *, max_document_text_length: int
) -> list[ValidationCheck]:
    records, manifest = load_dataset(dataset_dir)
    checks = validate_records(records, max_document_text_length=max_document_text_length)
    checks.append(
        _check(
            "manifest_record_count",
            manifest.record_count == len(records),
            "manifest record count matches files",
        )
    )
    checks.append(
        _check(
            "manifest_document_type_counts",
            manifest.document_type_counts == document_type_counts(records),
            "manifest document-type counts match files",
        )
    )
    checks.append(
        _check(
            "manifest_annotation_label_counts",
            manifest.annotation_label_counts == annotation_label_counts(records),
            "manifest annotation-label counts match files",
        )
    )
    for file_name, expected in manifest.file_checksums.items():
        actual = sha256_file(dataset_dir / file_name)
        checks.append(
            _check(f"checksum:{file_name}", actual == expected, f"checksum matches for {file_name}")
        )
    canonical_documents = [record.document.model_dump_json() for record in records]
    duplicates = sum(count - 1 for count in Counter(canonical_documents).values() if count > 1)
    checks.append(
        _check("no_duplicate_canonical_records", duplicates == 0, "no duplicate canonical records")
    )
    supported = {item.value for item in ClinicalDocumentType}
    actual_types = {record.document.document_type.value for record in records}
    checks.append(
        _check(
            "supported_document_types",
            actual_types.issubset(supported),
            "only supported document types exist",
        )
    )
    return checks


def validation_status(checks: list[ValidationCheck]) -> str:
    return "failed" if any(check.status == "failed" for check in checks) else "passed"
