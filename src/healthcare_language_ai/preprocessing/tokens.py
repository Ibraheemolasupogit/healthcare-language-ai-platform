"""Rule-based lexical token statistics."""

from __future__ import annotations

import re

TOKENISER_VERSION = "1.0.0"
TOKEN_PATTERN = re.compile(r"SYN-[A-Z]+-\d+|\d+(?:\.\d+)?|[A-Za-z]+(?:-[A-Za-z]+)?|[^\w\s]")
SYNTHETIC_ID_PATTERN = re.compile(r"^SYN-[A-Z]+-\d+$")


def lexical_tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def token_statistics(text: str) -> dict[str, int | float]:
    tokens = lexical_tokens(text)
    lengths = [len(token) for token in tokens]
    return {
        "token_count": len(tokens),
        "unique_token_count": len({token.casefold() for token in tokens}),
        "alphabetic_token_count": sum(token.isalpha() for token in tokens),
        "numeric_token_count": sum(bool(re.fullmatch(r"\d+(?:\.\d+)?", token)) for token in tokens),
        "punctuation_token_count": sum(bool(re.fullmatch(r"[^\w\s]", token)) for token in tokens),
        "synthetic_identifier_token_count": sum(
            bool(SYNTHETIC_ID_PATTERN.match(token)) for token in tokens
        ),
        "average_token_length": round(sum(lengths) / len(lengths), 4) if lengths else 0.0,
        "maximum_token_length": max(lengths) if lengths else 0,
    }
