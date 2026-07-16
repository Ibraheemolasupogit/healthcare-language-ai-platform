from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import validate

from healthcare_language_ai.embeddings.local_sentence_transformer import (
    DeterministicTestEncoder,
    encode_with_injected_encoder,
    inspect_local_model,
)
from healthcare_language_ai.embeddings.model_metadata import directory_checksum
from healthcare_language_ai.embeddings.offline import reject_remote_identifier
from healthcare_language_ai.retrieval_quality.benchmark import generate_benchmark
from healthcare_language_ai.retrieval_quality.configurations import load_registry
from healthcare_language_ai.retrieval_quality.contracts import (
    BenchmarkSplit,
    RetrievalApprovalDecision,
)
from healthcare_language_ai.retrieval_quality.experiments import (
    compare_configurations,
    run_experiment,
    validate_comparison_dir,
    validate_experiment_dir,
)
from healthcare_language_ai.retrieval_quality.features import (
    expand_query_text,
    negation_compatibility,
    numeric_compatibility,
)
from healthcare_language_ai.retrieval_quality.holdout import validate_holdout_dir, write_holdout
from healthcare_language_ai.retrieval_quality.review import write_review_pack

HOLDOUT = Path("tests/fixtures/retrieval-quality/holdout")
BENCHMARK = Path("tests/fixtures/retrieval-quality/benchmark")
COMPARISON = Path("tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce")


def test_local_model_path_rejects_remote_identifier_and_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        reject_remote_identifier("sentence-transformers/all-MiniLM-L6-v2")
    with pytest.raises(FileNotFoundError):
        inspect_local_model(model_path=tmp_path / "missing")


def test_injected_encoder_validates_vectors() -> None:
    encoder = DeterministicTestEncoder(dimension=8)
    assert len(encode_with_injected_encoder(encoder, ["alpha"])[0]) == 8
    with pytest.raises(ValueError):
        encode_with_injected_encoder(DeterministicTestEncoder(invalid=True), ["alpha"])
    with pytest.raises(ValueError):
        encode_with_injected_encoder(DeterministicTestEncoder(mismatch=True), ["alpha"])


def test_model_directory_checksum_is_stable(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text('{"hidden_size": 8}', encoding="utf-8")
    assert directory_checksum(tmp_path) == directory_checksum(tmp_path)


def test_holdout_fixture_validates_and_reproduces(tmp_path: Path) -> None:
    generated = write_holdout(
        count=40,
        seed=7026,
        output_dir=tmp_path,
        reference_timestamp=datetime.fromisoformat("2026-01-09T09:00:00+00:00"),
    )
    assert validate_holdout_dir(HOLDOUT) == []
    assert (generated / "holdout_manifest.json").read_text() == (
        HOLDOUT / "holdout_manifest.json"
    ).read_text()


def test_benchmark_splits_do_not_overlap_and_reproduce(tmp_path: Path) -> None:
    generated = generate_benchmark(tmp_path, holdout_dir=HOLDOUT)
    split = BenchmarkSplit.model_validate_json((BENCHMARK / "benchmark_splits.json").read_text())
    assert not set(split.development_query_ids) & set(split.validation_query_ids)
    assert not set(split.holdout_query_ids) & set(split.validation_query_ids)
    assert (generated / "query_set_manifest.json").read_text() == (
        BENCHMARK / "query_set_manifest.json"
    ).read_text()


def test_query_expansion_negation_and_numeric_features_are_deterministic() -> None:
    expanded, rules = expand_query_text("CT history BP")
    assert "computed tomography" in expanded
    assert any(rule.expansion_type == "section_alias" for rule in rules)
    assert negation_compatibility("no swelling", "swelling observed") < 1.0
    assert numeric_compatibility("8 mm value", "8 mm recorded") == 1.0
    assert numeric_compatibility("8 mm value", "9 cm recorded") < 1.0


def test_registry_identifies_optional_model_configuration() -> None:
    configs = load_registry(Path("config/retrieval-configurations.yaml"))
    ids = {config.configuration_id for config in configs}
    assert len(ids) == len(configs)
    assert any(config.requires_optional_model for config in configs)


def test_experiment_and_comparison_fixtures_validate_and_reproduce(tmp_path: Path) -> None:
    experiment = run_experiment(
        configuration_id="feature_reranked_hybrid_v1",
        benchmark_dir=BENCHMARK,
        output_root=tmp_path / "experiments",
        reference_timestamp=datetime.fromisoformat("2026-01-10T09:00:00+00:00"),
    )
    assert validate_experiment_dir(experiment) == []
    comparison = compare_configurations(
        benchmark_dir=BENCHMARK,
        configuration_registry=Path("config/retrieval-configurations.yaml"),
        output_root=tmp_path / "comparison",
        reference_timestamp=datetime.fromisoformat("2026-01-11T09:00:00+00:00"),
    )
    assert validate_comparison_dir(comparison) == []
    decision = RetrievalApprovalDecision.model_validate_json(
        (comparison / "retrieval_approval_decision.json").read_text()
    )
    assert decision.approval_status == "not_approved"
    assert not decision.approved_for_future_rag_prototype


def test_review_pack_omits_full_source_documents(tmp_path: Path) -> None:
    generated = write_review_pack(benchmark_dir=BENCHMARK, output_dir=tmp_path)
    assert (generated / "review-manifest.json").exists()
    guidance = (generated / "review-guidance.md").read_text()
    assert "does not claim clinician validation" in guidance


def test_retrieval_quality_schemas_validate_fixture_evidence() -> None:
    schema_root = Path("schemas/retrieval_quality")
    validate(
        json.loads((HOLDOUT / "holdout_manifest.json").read_text()),
        json.loads((schema_root / "holdout-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((BENCHMARK / "benchmark_splits.json").read_text()),
        json.loads((schema_root / "benchmark-split.schema.json").read_text()),
    )
    validate(
        json.loads((COMPARISON / "comparison_manifest.json").read_text()),
        json.loads((schema_root / "comparison-manifest.schema.json").read_text()),
    )
