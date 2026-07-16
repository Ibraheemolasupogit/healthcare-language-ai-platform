from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from healthcare_language_ai.retrieval_remediation.contracts import (
    BenchmarkUpgradeManifest,
    RemediationApprovalDecision,
)
from healthcare_language_ai.retrieval_remediation.features import (
    char_similarity,
    expand_synonyms,
    pseudo_feedback_terms,
    synonym_graph_has_cycle,
)
from healthcare_language_ai.retrieval_remediation.pipeline import (
    validate_benchmark_dir,
    validate_comparison_dir,
    validate_experiment_dir,
    validate_failure_dir,
)
from healthcare_language_ai.retrieval_remediation.registry import load_registry

ROOT = Path("tests/fixtures/retrieval-remediation")
FAILURE = ROOT / "failures/RFAIL-43f65b8f8118261fe023e705"
BENCHMARK = ROOT / "benchmark-v2.1"
EXPERIMENT = ROOT / "experiments/REMEXP-41fd5fa127ab616f7f74cc9b"
COMPARISON = ROOT / "comparison/REMCOMP-1a3a8c86fc4567de3049f352"


def test_remediation_features_are_deterministic() -> None:
    assert char_similarity("computed tomography", "CT computed tomography scan") > 0.45
    expanded, additions = expand_synonyms("CT renal")
    assert "computed" in expanded
    assert "kidney" in additions
    assert pseudo_feedback_terms("renal review", ["renal kidney assessment stable"])
    assert not synonym_graph_has_cycle()


def test_remediation_registry_contains_required_configurations() -> None:
    configs = load_registry(Path("config/retrieval-remediation-configurations.yaml"))
    ids = {config.configuration_id for config in configs}
    assert len(configs) == 10
    assert "abstaining_ensemble_v1" in ids
    assert all(not config.description.lower().startswith("rag") for config in configs)


def test_remediation_fixture_evidence_validates() -> None:
    assert validate_failure_dir(FAILURE) == []
    assert validate_benchmark_dir(BENCHMARK) == []
    assert validate_experiment_dir(EXPERIMENT) == []
    assert validate_comparison_dir(COMPARISON) == []
    benchmark = BenchmarkUpgradeManifest.model_validate_json(
        (BENCHMARK / "query_set_manifest.json").read_text()
    )
    assert benchmark.benchmark_version == "2.1.0"
    assert benchmark.original_benchmark_mutation_status == "passed"
    decision = RemediationApprovalDecision.model_validate_json(
        (COMPARISON / "retrieval_approval_decision.json").read_text()
    )
    assert decision.approved_for_future_rag_prototype
    assert decision.failed_required_gates == 0


def test_retrieval_remediation_schemas_validate_fixture_evidence() -> None:
    schema_root = Path("schemas/retrieval_remediation")
    validate(
        json.loads((FAILURE / "failure_manifest.json").read_text()),
        json.loads((schema_root / "failure-analysis-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((BENCHMARK / "query_set_manifest.json").read_text()),
        json.loads((schema_root / "benchmark-upgrade-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((EXPERIMENT / "experiment_manifest.json").read_text()),
        json.loads((schema_root / "remediation-experiment-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((COMPARISON / "comparison_manifest.json").read_text()),
        json.loads((schema_root / "remediation-comparison-manifest.schema.json").read_text()),
    )
