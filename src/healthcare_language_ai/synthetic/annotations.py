"""Helpers for exact text-span annotation creation."""

from __future__ import annotations

from healthcare_language_ai.synthetic.models import EntityAnnotation


def span_annotation(
    text: str, *, label: str, value: str, normalised_value: str | None = None
) -> EntityAnnotation:
    """Create an annotation whose offsets match the first exact text occurrence."""
    start = text.index(value)
    end = start + len(value)
    return EntityAnnotation(
        label=label,
        value=value,
        start=start,
        end=end,
        normalised_value=normalised_value or value,
    )
