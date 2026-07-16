"""Deterministic hash-vector embeddings for offline retrieval baselines."""

from __future__ import annotations

import hashlib
import math

from healthcare_language_ai.retrieval.tokenisation import ngrams, tokens

HASH_EMBEDDING_VERSION = "1.0.0"


def hash_vector(
    text: str, *, dimension: int, ngram_min: int = 1, ngram_max: int = 2
) -> list[float]:
    """Return a signed, L2-normalised feature-hash vector using SHA-256."""
    vector = [0.0 for _ in range(dimension)]
    for token in ngrams(tokens(text), ngram_min=ngram_min, ngram_max=ngram_max):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % dimension
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 10) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return round(sum(a * b for a, b in zip(left, right, strict=True)), 10)
