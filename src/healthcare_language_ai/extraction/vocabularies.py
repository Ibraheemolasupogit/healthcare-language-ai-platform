"""Controlled local vocabularies for deterministic extraction."""

from __future__ import annotations

from healthcare_language_ai.extraction.contracts import (
    SUPPORTED_ENTITY_LABELS,
    VocabularyEntry,
)
from healthcare_language_ai.synthetic import vocabularies as synthetic_vocab
from healthcare_language_ai.utils.identifiers import deterministic_id

VOCABULARY_VERSION = "1.0.0"

_CATEGORY_VALUES = {
    "administrative_priority": synthetic_vocab.ADMINISTRATIVE_PRIORITIES,
    "body_site": synthetic_vocab.BODY_SITES,
    "descriptor": synthetic_vocab.REPORT_DESCRIPTORS,
    "encounter_context": synthetic_vocab.ENCOUNTER_CONTEXTS,
    "investigation": synthetic_vocab.INVESTIGATIONS,
    "observation": synthetic_vocab.OBSERVATIONS,
    "presenting_concern": synthetic_vocab.PRESENTING_CONCERNS,
    "specialty": synthetic_vocab.SPECIALTIES,
    "workflow_status": synthetic_vocab.WORKFLOW_STATUSES,
}

_SECTION_HINTS = {
    "administrative_priority": ["administrative priority label"],
    "body_site": ["assessment summary", "current concerns", "findings", "specimen type"],
    "descriptor": ["current concerns", "findings", "macroscopic description"],
    "encounter_context": [
        "relevant history",
        "relevant synthetic history",
        "synthetic hospital course summary",
    ],
    "investigation": ["recorded investigations", "study"],
    "observation": ["observations"],
    "presenting_concern": [
        "admission reason",
        "reason for attendance",
        "referral reason",
        "synthetic indication",
    ],
    "specialty": ["microscopic description", "requested review"],
    "workflow_status": ["discharge status", "synthetic interpretation label"],
}


def load_vocabulary() -> list[VocabularyEntry]:
    """Return active controlled vocabulary entries in deterministic order."""
    entries: list[VocabularyEntry] = []
    for label, values in sorted(_CATEGORY_VALUES.items()):
        if label not in SUPPORTED_ENTITY_LABELS:
            msg = f"unsupported extraction label configured: {label}"
            raise ValueError(msg)
        for value in sorted(values):
            entry_id = "VOC_" + deterministic_id(
                {"label": label, "value": value, "version": VOCABULARY_VERSION}, length=20
            )
            entries.append(
                VocabularyEntry(
                    vocabulary_entry_id=entry_id,
                    canonical_value=value,
                    surface_forms=[value],
                    label=label,
                    document_types=[],
                    section_labels=sorted(_SECTION_HINTS.get(label, [])),
                    case_sensitive=False,
                    word_boundary_required=True,
                    priority=10,
                    active=True,
                    vocabulary_version=VOCABULARY_VERSION,
                )
            )
    return sorted(entries, key=lambda item: (item.label, item.canonical_value))
