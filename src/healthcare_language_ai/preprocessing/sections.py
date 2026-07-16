"""Rule-based section parsing for synthetic clinical documents."""

from __future__ import annotations

import re

from healthcare_language_ai.preprocessing.contracts import ProcessedSection
from healthcare_language_ai.preprocessing.normalisation import checksum_text
from healthcare_language_ai.utils.identifiers import deterministic_id

SECTION_PARSER_VERSION = "1.0.0"
KNOWN_HEADINGS = {
    "reason for attendance",
    "relevant history",
    "observations",
    "assessment summary",
    "plan recorded for simulation",
    "admission reason",
    "synthetic hospital-course summary",
    "recorded investigations",
    "discharge status",
    "follow-up placeholder",
    "referral reason",
    "relevant synthetic history",
    "current concerns",
    "requested review",
    "administrative priority label",
    "study",
    "synthetic indication",
    "findings",
    "impression",
    "specimen type",
    "macroscopic description",
    "microscopic description",
    "synthetic interpretation label",
}


def _normalise_label(label: str) -> str:
    return label.strip().casefold().replace("-", " ")


def parse_sections(text: str, *, document_id: str, run_id: str) -> list[ProcessedSection]:
    pattern = re.compile(r"(?m)^([^:\n]{2,80}):\s*")
    matches = list(pattern.finditer(text))
    sections: list[ProcessedSection] = []
    if not matches:
        return [
            ProcessedSection(
                section_id=deterministic_id(
                    [run_id, document_id, 1, "unknown"], prefix="SEC", length=24
                ),
                document_id=document_id,
                section_index=1,
                section_label="unknown",
                normalised_section_label="unknown",
                heading_start=0,
                heading_end=0,
                content_start=0,
                content_end=len(text),
                section_text=text,
                section_text_checksum=checksum_text(text),
                parser_rule="whole_document_unknown",
                preprocessing_run_id=run_id,
            )
        ]
    for index, match in enumerate(matches, start=1):
        label = match.group(1).strip()
        next_start = matches[index].start() if index < len(matches) else len(text)
        content_start = match.end()
        content_end = next_start
        section_text = text[content_start:content_end]
        normalised = _normalise_label(label)
        rule = "known_heading" if normalised in KNOWN_HEADINGS else "unknown_heading"
        sections.append(
            ProcessedSection(
                section_id=deterministic_id(
                    [run_id, document_id, index, label], prefix="SEC", length=24
                ),
                document_id=document_id,
                section_index=index,
                section_label=label,
                normalised_section_label=normalised,
                heading_start=match.start(1),
                heading_end=match.end(1),
                content_start=content_start,
                content_end=content_end,
                section_text=section_text,
                section_text_checksum=checksum_text(section_text),
                parser_rule=rule,
                preprocessing_run_id=run_id,
            )
        )
    return sections
