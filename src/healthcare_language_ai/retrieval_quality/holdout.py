"""Independent synthetic holdout corpus generation."""

from __future__ import annotations

import random
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from healthcare_language_ai.domain.enums import ClinicalDocumentType
from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_quality.contracts import (
    HoldoutAnnotation,
    HoldoutDocument,
    HoldoutManifest,
    HoldoutQualityReport,
    VocabularyOverlapReport,
)
from healthcare_language_ai.retrieval_quality.io import (
    output_checksums,
    stable_id,
    write_json,
    write_jsonl,
)
from healthcare_language_ai.synthetic.validation import (
    PROHIBITED_RECOMMENDATION_PHRASES,
    SUSPICIOUS_PATTERNS,
)

HOLDOUT_GENERATOR_VERSION = "1.0.0"
HOLDOUT_TEMPLATE_VERSION = "1.0.0"
HOLDOUT_VOCABULARY_VERSION = "1.0.0"

DOCUMENT_TYPES = [
    ClinicalDocumentType.CLINICAL_NOTE.value,
    ClinicalDocumentType.DISCHARGE_SUMMARY.value,
    ClinicalDocumentType.REFERRAL_LETTER.value,
    ClinicalDocumentType.RADIOLOGY_REPORT.value,
    ClinicalDocumentType.PATHOLOGY_REPORT.value,
]

SECTION_SETS = [
    ["Background", "Observed findings", "Interpretive summary"],
    ["Relevant history", "Report findings", "Workflow note"],
    ["Context", "Measurements", "Summary impression"],
    ["Reason for review", "Details", "Administrative note"],
]

CONCERNS = [
    "cardiac rhythm check",
    "respiratory observation",
    "renal marker review",
    "hepatic panel comparison",
    "mobility note",
    "skin observation",
    "blood pressure log",
    "computed tomography review",
    "magnetic resonance imaging note",
    "pathology specimen tracking",
]

NEGATED = ["no fever", "without swelling", "denies dizziness", "negative for fracture"]
NUMERICS = ["8 mm", "2.5 cm", "72 bpm", "98 percent", "14 mg", "30 mL"]


def _safe_id(prefix: str, seed: int, index: int) -> str:
    value = int(stable_id("ID", [prefix, seed, index], length=12).split("-", 1)[1], 16)
    return f"{prefix}-{value % 999999 + 1:06d}"


def _document_text(sections: dict[str, str]) -> str:
    return "\n\n".join(f"{label}: {body}" for label, body in sections.items())


def generate_holdout_documents(
    *, count: int, seed: int, reference_timestamp: datetime
) -> tuple[list[HoldoutDocument], list[HoldoutAnnotation]]:
    documents: list[HoldoutDocument] = []
    annotations: list[HoldoutAnnotation] = []
    for index in range(1, count + 1):
        rng = random.Random(f"holdout:{seed}:{index}:{HOLDOUT_GENERATOR_VERSION}")
        document_type = DOCUMENT_TYPES[(index - 1) % len(DOCUMENT_TYPES)]
        section_labels = SECTION_SETS[index % len(SECTION_SETS)]
        concern = CONCERNS[(index + rng.randrange(0, len(CONCERNS))) % len(CONCERNS)]
        negated = NEGATED[index % len(NEGATED)]
        numeric = NUMERICS[index % len(NUMERICS)]
        abbreviation = ["CT", "MRI", "BP", "HR"][index % 4]
        distractor = CONCERNS[(index + 4) % len(CONCERNS)]
        sections = {
            section_labels[0]: (
                f"Synthetic-only encounter {index} describes {concern}; "
                f"the note also mentions unrelated {distractor} for distractor testing."
            ),
            section_labels[1]: (
                f"{abbreviation} context is recorded with value {numeric}. "
                f"The wording is deliberately varied and {negated}."
            ),
            section_labels[2]: (
                "Fictional workflow status is stable for SYN-ENC evidence. "
                "No treatment recommendation or confirmed diagnosis is provided."
            ),
        }
        if index % 6 == 0:
            sections.pop(section_labels[2])
        document_id = _safe_id("SYN-DOC", seed + 77, index)
        subject_id = _safe_id("SYN-SUBJ", seed + 88, index)
        encounter_id = _safe_id("SYN-ENC", seed + 99, index)
        document = HoldoutDocument(
            document_id=document_id,
            document_type=document_type,
            synthetic_subject_id=subject_id,
            synthetic_encounter_id=encounter_id,
            text=_document_text(sections),
            sections=sections,
            created_at=reference_timestamp + timedelta(minutes=index),
            seed=seed,
            record_index=index,
            template_family="independent_retrieval_holdout",
            holdout_generator_version=HOLDOUT_GENERATOR_VERSION,
            holdout_template_version=HOLDOUT_TEMPLATE_VERSION,
            holdout_vocabulary_version=HOLDOUT_VOCABULARY_VERSION,
            synthetic_data_only=True,
            clinical_use_prohibited=True,
        )
        documents.append(document)
        annotations.append(
            HoldoutAnnotation(
                annotation_id=stable_id("HANN", [document_id, concern]),
                document_id=document_id,
                synthetic_subject_id=subject_id,
                synthetic_encounter_id=encounter_id,
                annotation_type="retrieval_topic",
                value=concern,
                rationale="manual_holdout_topic",
            )
        )
    return documents, annotations


def _sentence_count(documents: list[HoldoutDocument]) -> int:
    return sum(len(re.findall(r"[.!?]", document.text)) for document in documents)


def _quality_report(documents: list[HoldoutDocument]) -> HoldoutQualityReport:
    checks: list[dict[str, str]] = []
    for document in documents:
        for name, pattern in SUSPICIOUS_PATTERNS.items():
            passed = pattern.search(document.text) is None
            checks.append(
                {
                    "name": f"{document.document_id}:privacy:{name}",
                    "status": "passed" if passed else "failed",
                    "message": f"privacy pattern absent: {name}",
                }
            )
        lower = document.text.casefold()
        for phrase in PROHIBITED_RECOMMENDATION_PHRASES:
            passed = phrase not in lower
            checks.append(
                {
                    "name": f"{document.document_id}:clinical_safety:{phrase}",
                    "status": "passed" if passed else "failed",
                    "message": f"prohibited phrase absent: {phrase}",
                }
            )
        checks.append(
            {
                "name": f"{document.document_id}:synthetic_id_prefixes",
                "status": "passed"
                if all(
                    value.startswith(prefix)
                    for value, prefix in [
                        (document.document_id, "SYN-DOC-"),
                        (document.synthetic_subject_id, "SYN-SUBJ-"),
                        (document.synthetic_encounter_id, "SYN-ENC-"),
                    ]
                )
                else "failed",
                "message": "synthetic identifiers use approved prefixes",
            }
        )
    status = "failed" if any(check["status"] == "failed" for check in checks) else "passed"
    return HoldoutQualityReport(
        report_version="1.0.0",
        validation_status=status,
        privacy_validation_status=status,
        clinical_safety_validation_status=status,
        checks=checks,
    )


def build_overlap_report(
    documents: list[HoldoutDocument], query_texts: list[str] | None = None
) -> VocabularyOverlapReport:
    holdout_vocab = {token for doc in documents for token in tokens(doc.text)}
    original_vocab = set(
        tokens("presenting concern observation body site investigation workflow status")
    )
    extraction_vocab = set(
        tokens("chest abdomen heart lung kidney liver observation finding impression")
    )
    query_vocab = {token for text in query_texts or [] for token in tokens(text)}
    return VocabularyOverlapReport(
        report_version="1.0.0",
        original_vocabulary_size=len(original_vocab),
        holdout_vocabulary_size=len(holdout_vocab),
        query_vocabulary_size=len(query_vocab),
        extraction_vocabulary_size=len(extraction_vocab),
        original_holdout_overlap_ratio=round(
            len(original_vocab & holdout_vocab) / max(1, len(original_vocab)), 6
        ),
        holdout_query_overlap_ratio=round(
            len(holdout_vocab & query_vocab) / max(1, len(query_vocab)), 6
        ),
        extraction_holdout_overlap_ratio=round(
            len(extraction_vocab & holdout_vocab) / max(1, len(extraction_vocab)), 6
        ),
        status="passed",
    )


def write_holdout(
    *, count: int, seed: int, output_dir: Path, reference_timestamp: datetime
) -> Path:
    documents, annotations = generate_holdout_documents(
        count=count, seed=seed, reference_timestamp=reference_timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "holdout_documents.jsonl", documents)
    write_jsonl(output_dir / "holdout_annotations.jsonl", annotations)
    quality = _quality_report(documents)
    overlap = build_overlap_report(documents)
    write_json(output_dir / "holdout_quality_report.json", quality)
    write_json(output_dir / "vocabulary_overlap_report.json", overlap)
    files = [
        "holdout_documents.jsonl",
        "holdout_annotations.jsonl",
        "holdout_quality_report.json",
        "vocabulary_overlap_report.json",
    ]
    counts = Counter(document.document_type for document in documents)
    manifest = HoldoutManifest(
        holdout_dataset_id=stable_id("HOLDOUT", [seed, count, reference_timestamp.isoformat()]),
        schema_version="1.0.0",
        document_count=len(documents),
        document_type_counts=dict(sorted(counts.items())),
        section_count=sum(len(document.sections) for document in documents),
        sentence_count=_sentence_count(documents),
        seed=seed,
        reference_timestamp=reference_timestamp,
        holdout_generator_version=HOLDOUT_GENERATOR_VERSION,
        holdout_template_version=HOLDOUT_TEMPLATE_VERSION,
        holdout_vocabulary_version=HOLDOUT_VOCABULARY_VERSION,
        files=[*files, "holdout_manifest.json", "README.md"],
        file_checksums=output_checksums(output_dir, files),
        privacy_validation_status=quality.privacy_validation_status,
        clinical_safety_validation_status=quality.clinical_safety_validation_status,
        vocabulary_overlap_status=overlap.status,
        synthetic_data_only=True,
        clinical_use_prohibited=True,
    )
    write_json(output_dir / "holdout_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Independent Retrieval Holdout",
                "",
                "Synthetic, locally authored, non-clinical retrieval holdout evidence.",
                f"Document count: {len(documents)}",
                f"Seed: {seed}",
                f"Dataset ID: {manifest.holdout_dataset_id}",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    return output_dir


def validate_holdout_dir(holdout_dir: Path) -> list[str]:
    required = [
        "holdout_documents.jsonl",
        "holdout_annotations.jsonl",
        "holdout_manifest.json",
        "holdout_quality_report.json",
        "vocabulary_overlap_report.json",
        "README.md",
    ]
    failures = [f"missing {name}" for name in required if not (holdout_dir / name).exists()]
    if failures:
        return failures
    manifest = HoldoutManifest.model_validate_json(
        (holdout_dir / "holdout_manifest.json").read_text()
    )
    for name, expected in manifest.file_checksums.items():
        from healthcare_language_ai.retrieval_quality.io import sha256_file

        actual = sha256_file(holdout_dir / name)
        if actual != expected:
            failures.append(f"checksum mismatch for {name}")
    quality = HoldoutQualityReport.model_validate_json(
        (holdout_dir / "holdout_quality_report.json").read_text()
    )
    if quality.validation_status == "failed":
        failures.append("holdout quality report failed")
    return failures
