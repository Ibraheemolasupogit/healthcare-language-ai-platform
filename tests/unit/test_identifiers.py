from __future__ import annotations

import re

from healthcare_language_ai.utils.identifiers import deterministic_id, new_uuid


def test_deterministic_identifier_stability() -> None:
    payload = {"b": 2, "a": ["x", "y"]}
    assert deterministic_id(payload) == deterministic_id({"a": ["x", "y"], "b": 2})


def test_deterministic_identifier_changes_when_input_changes() -> None:
    first = deterministic_id({"document": "one"})
    second = deterministic_id({"document": "two"})
    assert first != second


def test_random_identifier_format() -> None:
    value = new_uuid()
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        value,
    )


def test_prefixed_identifier() -> None:
    assert deterministic_id({"x": 1}, prefix="doc").startswith("doc_")
    assert new_uuid(prefix="run").startswith("run_")
