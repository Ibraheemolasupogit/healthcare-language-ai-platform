"""Versioned lexical tokenisation for local retrieval."""

from __future__ import annotations

import re
import unicodedata

TOKENISER_VERSION = "1.0.0"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+|[a-z]+[a-z0-9]*|\d+(?:\.\d+)?")


def tokens(text: str) -> list[str]:
    """Return deterministic lexical tokens without removing negation or numbers."""
    normalised = unicodedata.normalize("NFC", text).casefold()
    return [match.group(0) for match in TOKEN_PATTERN.finditer(normalised)]


def ngrams(items: list[str], *, ngram_min: int = 1, ngram_max: int = 2) -> list[str]:
    generated: list[str] = []
    for size in range(ngram_min, ngram_max + 1):
        for index in range(0, max(0, len(items) - size + 1)):
            generated.append(" ".join(items[index : index + size]))
    return generated
