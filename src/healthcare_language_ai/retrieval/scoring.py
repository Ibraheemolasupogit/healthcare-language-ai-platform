"""Deterministic retrieval scoring algorithms."""

from __future__ import annotations

import math
from collections import Counter

from healthcare_language_ai.embeddings.hashing import cosine, hash_vector
from healthcare_language_ai.retrieval.contracts import RetrievalQuery, RetrievalUnit
from healthcare_language_ai.retrieval.tokenisation import tokens

KEYWORD_VERSION = "1.0.0"
TFIDF_VERSION = "1.0.0"
BM25_VERSION = "1.0.0"
HYBRID_VERSION = "1.0.0"
SCORE_NORMALISATION_VERSION = "1.0.0"


def vocabulary(units: list[RetrievalUnit]) -> list[str]:
    return sorted({token for unit in units for token in tokens(unit.text)})


def document_frequency(units: list[RetrievalUnit]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for unit in units:
        counts.update(set(tokens(unit.text)))
    return dict(sorted(counts.items()))


def idf(df: int, corpus_size: int) -> float:
    return math.log((1 + corpus_size) / (1 + df)) + 1


def tfidf_vector(
    text: str, vocab: list[str], dfs: dict[str, int], corpus_size: int
) -> dict[str, float]:
    counts = Counter(tokens(text))
    total = sum(counts.values()) or 1
    return {
        token: round((counts[token] / total) * idf(dfs.get(token, 0), corpus_size), 10)
        for token in vocab
        if counts[token]
    }


def sparse_cosine(left: dict[str, float], right: dict[str, float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot = sum(left.get(key, 0.0) * value for key, value in right.items())
    return round(dot / (left_norm * right_norm), 10)


def keyword_score(query: RetrievalQuery, unit: RetrievalUnit) -> tuple[float, list[str]]:
    query_tokens = tokens(query.query_text)
    unit_tokens = set(tokens(unit.text))
    if not query_tokens:
        return 0.0, []
    matched = sorted(set(query_tokens) & unit_tokens)
    coverage = len(matched) / len(set(query_tokens))
    phrase_bonus = 0.25 if query.query_text.casefold() in unit.text.casefold() else 0.0
    return round(min(1.0, coverage + phrase_bonus), 10), matched


def bm25_score(
    query: RetrievalQuery,
    unit: RetrievalUnit,
    *,
    dfs: dict[str, int],
    corpus_size: int,
    average_length: float,
    k1: float,
    b: float,
) -> float:
    counts = Counter(tokens(unit.text))
    unit_length = sum(counts.values()) or 1
    score = 0.0
    for token in set(tokens(query.query_text)):
        freq = counts[token]
        if freq == 0:
            continue
        token_idf = math.log(
            1 + (corpus_size - dfs.get(token, 0) + 0.5) / (dfs.get(token, 0) + 0.5)
        )
        denominator = freq + k1 * (1 - b + b * (unit_length / average_length))
        score += token_idf * ((freq * (k1 + 1)) / denominator)
    return round(score, 10)


def metadata_score(query: RetrievalQuery, unit: RetrievalUnit) -> float:
    if not query.metadata_filters:
        return 0.0
    values = {
        "document_type": unit.document_type,
        "section_label": unit.section_label or "",
        "unit_type": unit.unit_type.value,
        "synthetic_subject_id": unit.synthetic_subject_id,
        "synthetic_encounter_id": unit.synthetic_encounter_id,
    }
    matched = sum(values.get(key) == value for key, value in query.metadata_filters.items())
    return round(matched / len(query.metadata_filters), 10)


def passes_filters(query: RetrievalQuery, unit: RetrievalUnit) -> bool:
    supported = {
        "document_type": unit.document_type,
        "section_label": unit.section_label or "",
        "unit_type": unit.unit_type.value,
        "synthetic_subject_id": unit.synthetic_subject_id,
        "synthetic_encounter_id": unit.synthetic_encounter_id,
    }
    unsupported = set(query.metadata_filters).difference(supported)
    if unsupported:
        msg = f"unsupported retrieval filter(s): {sorted(unsupported)}"
        raise ValueError(msg)
    return all(supported[key] == value for key, value in query.metadata_filters.items())


def normalise_scores(scores: list[float]) -> list[float]:
    if not scores:
        return []
    maximum = max(scores)
    if maximum <= 0:
        return [0.0 for _ in scores]
    return [round(score / maximum, 10) for score in scores]


def dense_score(query: RetrievalQuery, unit: RetrievalUnit, *, dimension: int) -> float:
    return cosine(
        hash_vector(query.query_text, dimension=dimension),
        hash_vector(unit.text, dimension=dimension),
    )
