"""Deterministic exact phrase matcher for controlled clinical vocabulary."""

from __future__ import annotations

import re

from healthcare_language_ai.extraction.contracts import ExtractionRule, RuleMatch, VocabularyEntry
from healthcare_language_ai.preprocessing.contracts import (
    ProcessedClinicalDocument,
    ProcessedSection,
    ProcessedSentence,
)
from healthcare_language_ai.utils.identifiers import deterministic_id


def _phrase_pattern(phrase: str, *, word_boundary: bool) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    pattern = rf"(?<!\w){escaped}(?!\w)" if word_boundary else escaped
    return re.compile(pattern, flags=re.IGNORECASE)


def _find_section(
    sections: list[ProcessedSection], document_id: str, start: int, end: int
) -> ProcessedSection:
    for section in sections:
        if (
            section.document_id == document_id
            and section.content_start <= start
            and end <= section.content_end
        ):
            return section
    return next(section for section in sections if section.document_id == document_id)


def _find_sentence(
    sentences: list[ProcessedSentence], document_id: str, start: int, end: int
) -> ProcessedSentence:
    for sentence in sentences:
        if (
            sentence.document_id == document_id
            and sentence.start_offset <= start
            and end <= sentence.end_offset
        ):
            return sentence
    return next(sentence for sentence in sentences if sentence.document_id == document_id)


def match_candidates(
    *,
    documents: list[ProcessedClinicalDocument],
    sections: list[ProcessedSection],
    sentences: list[ProcessedSentence],
    entries: list[VocabularyEntry],
    rules: list[ExtractionRule],
    extraction_run_id: str,
) -> list[RuleMatch]:
    """Generate deterministic phrase-match candidates over normalised text."""
    rule_by_entry = {rule.vocabulary_entry_id: rule for rule in rules}
    candidates: list[RuleMatch] = []
    for document in sorted(documents, key=lambda item: item.document_id):
        for entry in entries:
            if not entry.active:
                continue
            if entry.document_types and document.document_type not in entry.document_types:
                continue
            rule = rule_by_entry[entry.vocabulary_entry_id]
            for surface_form in sorted(entry.surface_forms, key=lambda item: (-len(item), item)):
                pattern = _phrase_pattern(surface_form, word_boundary=entry.word_boundary_required)
                for match in pattern.finditer(document.normalised_text):
                    start, end = match.span()
                    matched_text = document.normalised_text[start:end]
                    section = _find_section(sections, document.document_id, start, end)
                    if (
                        entry.section_labels
                        and section.normalised_section_label not in entry.section_labels
                    ):
                        continue
                    sentence = _find_sentence(sentences, document.document_id, start, end)
                    candidate_id = "CAND_" + deterministic_id(
                        {
                            "run": extraction_run_id,
                            "document_id": document.document_id,
                            "label": entry.label,
                            "start": start,
                            "end": end,
                            "rule_id": rule.rule_id,
                        },
                        length=24,
                    )
                    candidates.append(
                        RuleMatch(
                            candidate_id=candidate_id,
                            document_id=document.document_id,
                            label=entry.label,
                            value=entry.canonical_value,
                            normalised_value=entry.canonical_value.casefold(),
                            start_offset=start,
                            end_offset=end,
                            matched_text=matched_text,
                            section_id=section.section_id,
                            section_label=section.normalised_section_label,
                            sentence_id=sentence.sentence_id,
                            rule_id=rule.rule_id,
                            rule_version=rule.rule_version,
                            vocabulary_entry_id=entry.vocabulary_entry_id,
                            vocabulary_version=entry.vocabulary_version,
                            priority=rule.priority,
                            confidence=rule.confidence,
                            text_representation="normalised_text",
                            preprocessing_run_id=document.preprocessing_run_id,
                            extraction_run_id=extraction_run_id,
                        )
                    )
    return sorted(
        candidates,
        key=lambda item: (
            item.document_id,
            item.start_offset,
            item.end_offset,
            item.label,
            item.rule_id,
        ),
    )
