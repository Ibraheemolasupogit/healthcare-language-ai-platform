"""Transparent heading-based document and section classification."""

from __future__ import annotations

import json

from healthcare_language_ai.extraction.contracts import (
    DocumentClassificationPrediction,
    SectionClassificationPrediction,
)
from healthcare_language_ai.extraction.rules import CLASSIFICATION_RULE_VERSION
from healthcare_language_ai.preprocessing.contracts import (
    ProcessedClinicalDocument,
    ProcessedSection,
)

DOCUMENT_TYPE_HEADING_RULES = {
    "clinical_note": ["reason for attendance", "observations", "assessment summary"],
    "discharge_summary": ["admission reason", "discharge status", "follow up placeholder"],
    "pathology_report": [
        "specimen type",
        "macroscopic description",
        "microscopic description",
        "synthetic interpretation label",
    ],
    "radiology_report": ["study", "synthetic indication", "findings", "impression"],
    "referral_letter": ["referral reason", "requested review", "administrative priority label"],
}


def _confidence(score: int, heading_count: int) -> float:
    if heading_count == 0:
        return 0.0
    return round(min(1.0, 0.55 + (score / heading_count) * 0.45), 6)


def classify_documents(
    *,
    documents: list[ProcessedClinicalDocument],
    sections: list[ProcessedSection],
    extraction_run_id: str,
) -> list[DocumentClassificationPrediction]:
    sections_by_doc: dict[str, set[str]] = {}
    for section in sections:
        sections_by_doc.setdefault(section.document_id, set()).add(section.normalised_section_label)
    predictions: list[DocumentClassificationPrediction] = []
    for document in sorted(documents, key=lambda item: item.document_id):
        headings = sections_by_doc.get(document.document_id, set())
        scores = {
            document_type: sum(heading in headings for heading in required_headings)
            for document_type, required_headings in DOCUMENT_TYPE_HEADING_RULES.items()
        }
        predicted_type = sorted(scores, key=lambda item: (-scores[item], item))[0]
        matched = [
            f"CLS_{predicted_type}_{heading.replace(' ', '_')}"
            for heading in DOCUMENT_TYPE_HEADING_RULES[predicted_type]
            if heading in headings
        ]
        predictions.append(
            DocumentClassificationPrediction(
                document_id=document.document_id,
                predicted_document_type=predicted_type,
                confidence=_confidence(
                    scores[predicted_type],
                    len(DOCUMENT_TYPE_HEADING_RULES[predicted_type]),
                ),
                matched_rule_ids=";".join(sorted(matched)),
                score_by_class=json.dumps(scores, sort_keys=True, separators=(",", ":")),
                classification_rule_version=CLASSIFICATION_RULE_VERSION,
                extraction_run_id=extraction_run_id,
            )
        )
    return predictions


def classify_sections(
    *,
    sections: list[ProcessedSection],
    extraction_run_id: str,
) -> list[SectionClassificationPrediction]:
    return [
        SectionClassificationPrediction(
            section_id=section.section_id,
            document_id=section.document_id,
            predicted_section_label=section.normalised_section_label,
            confidence=1.0,
            classification_rule_version=CLASSIFICATION_RULE_VERSION,
            extraction_run_id=extraction_run_id,
        )
        for section in sorted(sections, key=lambda item: (item.document_id, item.section_index))
    ]
