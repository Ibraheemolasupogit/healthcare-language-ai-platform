"""Versioned deterministic text normalisation rules."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from healthcare_language_ai.preprocessing.contracts import TextTransformation
from healthcare_language_ai.utils.identifiers import deterministic_id

NORMALISATION_VERSION = "1.0.0"


def checksum_text(text: str) -> str:
    return deterministic_id(text, length=64)


def _record(name: str, before: str, after: str, version: str) -> TextTransformation:
    return TextTransformation(
        transformation_name=name,
        transformation_version=version,
        applied=before != after,
        change_count=0 if before == after else 1,
        before_checksum=checksum_text(before),
        after_checksum=checksum_text(after),
    )


def normalise_text(
    text: str,
    *,
    unicode_form: Literal["NFC", "NFKC"],
    tab_width: int,
    collapse_spaces: bool,
    preserve_final_newline: bool,
    version: str = NORMALISATION_VERSION,
) -> tuple[str, list[TextTransformation]]:
    """Apply conservative, documented normalisation without clinical inference."""
    transformations: list[TextTransformation] = []
    current = text
    updated = unicodedata.normalize(unicode_form, current)
    transformations.append(_record(f"unicode_{unicode_form}", current, updated, version))
    current = updated
    updated = current.replace("\r\n", "\n").replace("\r", "\n")
    transformations.append(_record("line_endings_to_lf", current, updated, version))
    current = updated
    updated = current.replace("\t", " " * tab_width)
    transformations.append(_record("tabs_to_spaces", current, updated, version))
    current = updated
    updated = "\n".join(line.rstrip(" ") for line in current.split("\n"))
    transformations.append(_record("trim_trailing_spaces", current, updated, version))
    current = updated
    if collapse_spaces:
        updated = "\n".join(
            re.sub(r"(?<=\S) {2,}(?=\S)", " ", line) for line in current.split("\n")
        )
        transformations.append(
            _record("collapse_repeated_inline_spaces", current, updated, version)
        )
        current = updated
    if preserve_final_newline and not current.endswith("\n"):
        updated = f"{current}\n"
    elif not preserve_final_newline:
        updated = current.rstrip("\n")
    else:
        updated = current
    transformations.append(_record("final_newline_policy", current, updated, version))
    return updated, transformations


def analytical_text(text: str) -> str:
    """Return analytical text without removing negation, digits, units, or identifiers."""
    punctuation = (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return re.sub(r"\s+", " ", punctuation.casefold()).strip()
