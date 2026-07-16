"""Build deterministic retrieval units from preprocessing evidence."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path

from healthcare_language_ai.retrieval.contracts import CorpusStatistics, RetrievalUnit
from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.utils.identifiers import deterministic_id


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unit_id(*, unit_type: str, source_id: str, corpus_version: str) -> str:
    return "RU_" + deterministic_id(
        {"unit_type": unit_type, "source_id": source_id, "corpus_version": corpus_version},
        length=24,
    )


def build_units(
    *,
    preprocessing_dir: Path,
    extraction_run_id: str,
    corpus_version: str,
    unit_type: str,
) -> list[RetrievalUnit]:
    docs = {
        row["document_id"]: row for row in _read_csv(preprocessing_dir / "processed_documents.csv")
    }
    sections = _read_csv(preprocessing_dir / "processed_sections.csv")
    sentences = _read_csv(preprocessing_dir / "processed_sentences.csv")
    requested = {"document", "section", "sentence"} if unit_type == "all" else {unit_type}
    units: list[RetrievalUnit] = []
    if "document" in requested:
        for doc in sorted(docs.values(), key=lambda item: item["document_id"]):
            text = doc["normalised_text"]
            units.append(
                RetrievalUnit(
                    retrieval_unit_id=unit_id(
                        unit_type="document",
                        source_id=doc["document_id"],
                        corpus_version=corpus_version,
                    ),
                    document_id=doc["document_id"],
                    unit_type="document",
                    document_type=doc["document_type"],
                    text=text,
                    text_checksum=checksum_text(text),
                    token_count=len(tokens(text)),
                    synthetic_subject_id=doc["synthetic_subject_id"],
                    synthetic_encounter_id=doc["synthetic_encounter_id"],
                    source_preprocessing_run_id=doc["preprocessing_run_id"],
                    source_extraction_run_id=extraction_run_id,
                    corpus_version=corpus_version,
                )
            )
    if "section" in requested:
        for section in sorted(
            sections, key=lambda item: (item["document_id"], int(item["section_index"]))
        ):
            doc = docs[section["document_id"]]
            text = section["section_text"]
            units.append(
                RetrievalUnit(
                    retrieval_unit_id=unit_id(
                        unit_type="section",
                        source_id=section["section_id"],
                        corpus_version=corpus_version,
                    ),
                    document_id=section["document_id"],
                    section_id=section["section_id"],
                    unit_type="section",
                    document_type=doc["document_type"],
                    section_label=section["normalised_section_label"],
                    text=text,
                    text_checksum=checksum_text(text),
                    token_count=len(tokens(text)),
                    synthetic_subject_id=doc["synthetic_subject_id"],
                    synthetic_encounter_id=doc["synthetic_encounter_id"],
                    source_preprocessing_run_id=doc["preprocessing_run_id"],
                    source_extraction_run_id=extraction_run_id,
                    corpus_version=corpus_version,
                )
            )
    if "sentence" in requested:
        section_by_id = {row["section_id"]: row for row in sections}
        for sentence in sorted(
            sentences, key=lambda item: (item["document_id"], int(item["document_sentence_index"]))
        ):
            doc = docs[sentence["document_id"]]
            section = section_by_id[sentence["section_id"]]
            text = sentence["sentence_text"]
            units.append(
                RetrievalUnit(
                    retrieval_unit_id=unit_id(
                        unit_type="sentence",
                        source_id=sentence["sentence_id"],
                        corpus_version=corpus_version,
                    ),
                    document_id=sentence["document_id"],
                    section_id=sentence["section_id"],
                    sentence_id=sentence["sentence_id"],
                    unit_type="sentence",
                    document_type=doc["document_type"],
                    section_label=section["normalised_section_label"],
                    text=text,
                    text_checksum=checksum_text(text),
                    token_count=len(tokens(text)),
                    synthetic_subject_id=doc["synthetic_subject_id"],
                    synthetic_encounter_id=doc["synthetic_encounter_id"],
                    source_preprocessing_run_id=doc["preprocessing_run_id"],
                    source_extraction_run_id=extraction_run_id,
                    corpus_version=corpus_version,
                )
            )
    return sorted(
        units,
        key=lambda item: (item.unit_type.value, item.document_id, item.retrieval_unit_id),
    )


def corpus_statistics(units: list[RetrievalUnit]) -> CorpusStatistics:
    token_lists = [tokens(unit.text) for unit in units]
    token_count = sum(len(items) for items in token_lists)
    unique = sorted({token for items in token_lists for token in items})
    lengths = [unit.token_count for unit in units] or [0]
    return CorpusStatistics(
        document_count=len({unit.document_id for unit in units}),
        section_count=sum(unit.unit_type.value == "section" for unit in units),
        sentence_count=sum(unit.unit_type.value == "sentence" for unit in units),
        retrieval_unit_count=len(units),
        token_count=token_count,
        unique_token_count=len(unique),
        document_type_distribution=dict(
            sorted(Counter(unit.document_type for unit in units).items())
        ),
        section_label_distribution=dict(
            sorted(Counter(unit.section_label or "" for unit in units).items())
        ),
        unit_type_distribution=dict(
            sorted(Counter(unit.unit_type.value for unit in units).items())
        ),
        average_unit_length=round(sum(lengths) / len(lengths), 6),
        minimum_unit_length=min(lengths),
        maximum_unit_length=max(lengths),
    )
