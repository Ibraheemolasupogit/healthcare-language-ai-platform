"""Rule construction and interpretable confidence scoring."""

from __future__ import annotations

from healthcare_language_ai.extraction.contracts import ExtractionRule, VocabularyEntry

ENTITY_RULE_VERSION = "1.0.0"
CLASSIFICATION_RULE_VERSION = "1.0.0"
OVERLAP_RESOLUTION_VERSION = "1.0.0"


def confidence_for(entry: VocabularyEntry) -> float:
    """Return deterministic, non-calibrated confidence from rule specificity."""
    if entry.document_types and entry.section_labels:
        return 1.0
    if entry.section_labels:
        return 0.95
    if entry.document_types:
        return 0.9
    return 0.85


def build_entity_rules(entries: list[VocabularyEntry]) -> list[ExtractionRule]:
    rules: list[ExtractionRule] = []
    for entry in entries:
        rules.append(
            ExtractionRule(
                rule_id=f"RULE_{entry.vocabulary_entry_id.removeprefix('VOC_')}",
                label=entry.label,
                vocabulary_entry_id=entry.vocabulary_entry_id,
                rule_version=ENTITY_RULE_VERSION,
                priority=entry.priority,
                confidence=confidence_for(entry),
            )
        )
    return sorted(rules, key=lambda item: item.rule_id)
