"""Dataset manifest and checksum helpers."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path

from healthcare_language_ai.synthetic.models import DatasetManifest, SyntheticDocumentRecord

DATASET_NAME = "synthetic_clinical_documents"
DATASET_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_type_counts(records: list[SyntheticDocumentRecord]) -> dict[str, int]:
    counts = Counter(record.document.document_type.value for record in records)
    return dict(sorted(counts.items()))


def annotation_label_counts(records: list[SyntheticDocumentRecord]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(entity.label for entity in record.annotation.entities)
    return dict(sorted(counts.items()))


def build_manifest(
    *,
    records: list[SyntheticDocumentRecord],
    seed: int,
    reference_timestamp: datetime,
    generator_version: str,
    template_version: str,
    vocabulary_version: str,
    file_checksums: dict[str, str],
) -> DatasetManifest:
    return DatasetManifest(
        dataset_name=DATASET_NAME,
        dataset_version=DATASET_VERSION,
        generator_version=generator_version,
        template_version=template_version,
        vocabulary_version=vocabulary_version,
        seed=seed,
        reference_timestamp=reference_timestamp,
        record_count=len(records),
        document_type_counts=document_type_counts(records),
        annotation_label_counts=annotation_label_counts(records),
        files=sorted(file_checksums),
        file_checksums=dict(sorted(file_checksums.items())),
        schema_version=SCHEMA_VERSION,
        synthetic_data_only=True,
        clinical_use_prohibited=True,
    )
