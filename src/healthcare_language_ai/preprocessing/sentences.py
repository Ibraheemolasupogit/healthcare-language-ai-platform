"""Deterministic rule-based sentence segmentation."""

from __future__ import annotations

import re

from healthcare_language_ai.preprocessing.contracts import ProcessedSection, ProcessedSentence
from healthcare_language_ai.preprocessing.normalisation import checksum_text
from healthcare_language_ai.preprocessing.tokens import lexical_tokens
from healthcare_language_ai.utils.identifiers import deterministic_id

SENTENCE_SEGMENTER_VERSION = "1.0.0"
NEGATION_RE = re.compile(r"\b(no|not|without|denies|none)\b", re.IGNORECASE)
NUMERIC_RE = re.compile(r"\d")
SYN_ID_RE = re.compile(r"SYN-[A-Z]+-\d+")


def segment_sentences(
    *,
    text: str,
    sections: list[ProcessedSection],
    run_id: str,
) -> list[ProcessedSentence]:
    sentences: list[ProcessedSentence] = []
    document_index = 1
    for section in sections:
        content = text[section.content_start : section.content_end]
        for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", content):
            sentence_text = match.group(0).strip()
            if not sentence_text:
                continue
            leading = len(match.group(0)) - len(match.group(0).lstrip())
            start = section.content_start + match.start() + leading
            end = start + len(sentence_text)
            tokens = lexical_tokens(sentence_text)
            sentences.append(
                ProcessedSentence(
                    sentence_id=deterministic_id(
                        [run_id, section.document_id, document_index, start, end],
                        prefix="SENT",
                        length=24,
                    ),
                    document_id=section.document_id,
                    section_id=section.section_id,
                    sentence_index=sum(
                        1 for item in sentences if item.section_id == section.section_id
                    )
                    + 1,
                    document_sentence_index=document_index,
                    start_offset=start,
                    end_offset=end,
                    sentence_text=sentence_text,
                    sentence_text_checksum=checksum_text(sentence_text),
                    token_count=len(tokens),
                    contains_negation_marker=bool(NEGATION_RE.search(sentence_text)),
                    contains_numeric_value=bool(NUMERIC_RE.search(sentence_text)),
                    contains_synthetic_identifier=bool(SYN_ID_RE.search(sentence_text)),
                    boundary_rule="punctuation_or_line_boundary",
                    preprocessing_run_id=run_id,
                )
            )
            document_index += 1
    return sentences
