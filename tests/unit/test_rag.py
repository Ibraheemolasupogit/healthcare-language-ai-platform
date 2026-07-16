from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from healthcare_language_ai.rag.contracts import RagEvaluationManifest, RagManifest
from healthcare_language_ai.rag.evidence import assemble_evidence_bundle, verify_retrieval_approval
from healthcare_language_ai.rag.local_generator import (
    inspect_local_generator,
    reject_remote_identifier,
)
from healthcare_language_ai.rag.pipeline import validate_evaluation_dir, validate_rag_dir
from healthcare_language_ai.rag.query_safety import classify_query

QUERY_DIR = Path("tests/fixtures/rag/queries")
RAG_DIR = Path("tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874")
EVAL_DIR = Path("tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017")
COMPARISON = Path(
    "tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352"
)


def test_retrieval_approval_loads_and_blocks_tampering(tmp_path: Path) -> None:
    approval = verify_retrieval_approval(COMPARISON)
    assert approval["retrieval_configuration_id"] == "abstaining_ensemble_v1"
    bad = tmp_path / "comparison"
    bad.mkdir()
    data = json.loads((COMPARISON / "comparison_manifest.json").read_text())
    data["approval_status"] = "not_approved"
    (bad / "comparison_manifest.json").write_text(json.dumps(data), encoding="utf-8")
    (bad / "retrieval_approval_decision.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        verify_retrieval_approval(bad)


def test_query_safety_blocks_unsupported_requests() -> None:
    assert classify_query("q1", "Synthetic summary request").allowed_for_retrieval
    blocked = classify_query("q2", "What medication dosage should I take?")
    assert not blocked.allowed_for_retrieval
    assert blocked.category == "unsupported_medication_request"


def test_rag_fixtures_validate_and_metrics_pass() -> None:
    assert validate_rag_dir(RAG_DIR) == []
    assert validate_evaluation_dir(EVAL_DIR) == []
    manifest = RagManifest.model_validate_json((RAG_DIR / "rag_manifest.json").read_text())
    assert manifest.retrieval_abstention_count == 5
    evaluation = RagEvaluationManifest.model_validate_json(
        (EVAL_DIR / "rag_evaluation_manifest.json").read_text()
    )
    assert evaluation.approved_for_local_synthetic_demo
    assert evaluation.failed_required_gates == 0
    assert evaluation.citation_validity_rate == 1.0


def test_evidence_limits_and_citation_labels_are_deterministic() -> None:
    first_query = json.loads((QUERY_DIR / "rag_queries.jsonl").read_text().splitlines()[0])
    from healthcare_language_ai.rag.contracts import RagQuery

    query = RagQuery.model_validate(first_query)
    bundle = assemble_evidence_bundle(
        rag_run_id="RAG-test",
        query=query,
        retrieval_approval_id="REMCOMP-test",
        maximum_evidence_units=2,
    )
    assert bundle.selected_unit_count <= 2
    assert [unit.citation_label for unit in bundle.evidence_units] == ["[E1]", "[E2]"]


def test_optional_local_generator_rejects_remote_identifiers(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        reject_remote_identifier("sentence-transformers/all-MiniLM-L6-v2")
    with pytest.raises(FileNotFoundError):
        inspect_local_generator(tmp_path / "missing")


def test_rag_json_schemas_validate_fixture_evidence() -> None:
    schema_root = Path("schemas/rag")
    validate(
        json.loads((QUERY_DIR / "rag_queries.jsonl").read_text().splitlines()[0]),
        json.loads((schema_root / "rag-query.schema.json").read_text()),
    )
    validate(
        json.loads((RAG_DIR / "rag_manifest.json").read_text()),
        json.loads((schema_root / "rag-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((EVAL_DIR / "rag_evaluation_manifest.json").read_text()),
        json.loads((schema_root / "rag-evaluation-manifest.schema.json").read_text()),
    )
