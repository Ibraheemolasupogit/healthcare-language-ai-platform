"""Model-free retrieval remediation features for Milestone 8."""

from __future__ import annotations

import math
import re
from collections import Counter

from healthcare_language_ai.retrieval.tokenisation import tokens

SYNONYM_GRAPH: dict[str, set[str]] = {
    "ct": {"computed", "tomography", "scan"},
    "mri": {"magnetic", "resonance", "imaging"},
    "bp": {"blood", "pressure"},
    "hr": {"heart", "rate"},
    "summary": {"impression", "overview"},
    "findings": {"observed", "observations"},
    "renal": {"kidney"},
    "cardiac": {"heart"},
    "respiratory": {"breathing", "lung"},
}


def char_ngrams(text: str, *, minimum: int = 3, maximum: int = 5) -> set[str]:
    normalised = re.sub(r"\s+", " ", text.lower()).strip()
    padded = f" {normalised} "
    return {
        padded[index : index + size]
        for size in range(minimum, maximum + 1)
        for index in range(max(0, len(padded) - size + 1))
    }


def char_similarity(left: str, right: str) -> float:
    left_ngrams = char_ngrams(left)
    right_ngrams = char_ngrams(right)
    if not left_ngrams or not right_ngrams:
        return 0.0
    return len(left_ngrams & right_ngrams) / len(left_ngrams | right_ngrams)


def phrase_score(query: str, text: str) -> float:
    query_tokens = tokens(query)
    text_lower = text.lower()
    if not query_tokens:
        return 0.0
    bigrams = [" ".join(query_tokens[index : index + 2]) for index in range(len(query_tokens) - 1)]
    if not bigrams:
        return 0.0
    return sum(1 for bigram in bigrams if bigram in text_lower) / len(bigrams)


def proximity_score(query: str, text: str) -> float:
    query_tokens = tokens(query)
    text_tokens = tokens(text)
    if len(query_tokens) < 2 or not text_tokens:
        return 0.0
    positions: dict[str, list[int]] = {}
    for index, token in enumerate(text_tokens):
        positions.setdefault(token, []).append(index)
    present = [positions[token][0] for token in query_tokens if token in positions]
    if len(present) < 2:
        return 0.0
    span = max(present) - min(present) + 1
    return min(1.0, len(present) / max(1, span))


def expand_synonyms(query: str) -> tuple[str, list[str]]:
    query_tokens = tokens(query)
    additions: list[str] = []
    for token in query_tokens:
        additions.extend(sorted(SYNONYM_GRAPH.get(token, set())))
    expanded = " ".join([query, *additions]).strip()
    return expanded, additions


def synonym_graph_has_cycle() -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in SYNONYM_GRAPH.get(node, set()):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in SYNONYM_GRAPH)


def pseudo_feedback_terms(query: str, candidate_texts: list[str], *, limit: int = 6) -> list[str]:
    blocked = set(tokens(query))
    blocked.update({"no", "not", "without", "negative", "positive"})
    counts: Counter[str] = Counter()
    for text in candidate_texts[:5]:
        counts.update(
            token for token in tokens(text) if token not in blocked and not token.isdigit()
        )
    return [term for term, _ in counts.most_common(limit)]


def reciprocal_rank_fusion(rankings: list[list[str]], *, k: int = 60) -> dict[str, float]:
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, unit_id in enumerate(ranking, start=1):
            fused[unit_id] = fused.get(unit_id, 0.0) + 1.0 / (k + rank)
    return fused


def confidence_score(top_score: float, second_score: float, agreement_count: int) -> float:
    margin = max(0.0, top_score - second_score)
    agreement = min(1.0, agreement_count / 3.0)
    return round(min(1.0, 0.25 + margin + (agreement * 0.45)), 6)


def ndcg(gains: list[int]) -> float:
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal = sum(
        gain / math.log2(index + 2) for index, gain in enumerate(sorted(gains, reverse=True))
    )
    return 0.0 if ideal == 0 else dcg / ideal
