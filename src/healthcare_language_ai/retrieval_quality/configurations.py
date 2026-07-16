"""Versioned retrieval configuration registry."""

from __future__ import annotations

from pathlib import Path

import yaml

from healthcare_language_ai.retrieval_quality.contracts import RetrievalConfiguration
from healthcare_language_ai.retrieval_quality.io import write_json

CONFIGURATION_REGISTRY_VERSION = "1.0.0"


def default_configurations() -> list[RetrievalConfiguration]:
    return [
        RetrievalConfiguration(
            configuration_id="bm25_v2",
            name="BM25 v2",
            candidate_strategy="bm25",
            candidate_top_k=10,
            embedding_provider="none",
            query_expansion_enabled=False,
            negation_features_enabled=False,
            numeric_features_enabled=False,
            abbreviation_expansion_enabled=False,
            section_aliases_enabled=False,
            granularity_policy="single_granularity",
            reranker="none",
            final_top_k=5,
            weights={"bm25": 1.0},
            requires_optional_model=False,
            active=True,
            complexity_rank=1,
        ),
        RetrievalConfiguration(
            configuration_id="query_expanded_bm25_v1",
            name="Query-expanded BM25",
            candidate_strategy="bm25",
            candidate_top_k=10,
            embedding_provider="none",
            query_expansion_enabled=True,
            negation_features_enabled=False,
            numeric_features_enabled=False,
            abbreviation_expansion_enabled=True,
            section_aliases_enabled=True,
            granularity_policy="single_granularity",
            reranker="none",
            final_top_k=5,
            weights={"bm25": 0.9, "expansion": 0.1},
            requires_optional_model=False,
            active=True,
            complexity_rank=2,
        ),
        RetrievalConfiguration(
            configuration_id="negation_numeric_bm25_v1",
            name="Negation and numeric BM25",
            candidate_strategy="bm25",
            candidate_top_k=10,
            embedding_provider="none",
            query_expansion_enabled=True,
            negation_features_enabled=True,
            numeric_features_enabled=True,
            abbreviation_expansion_enabled=True,
            section_aliases_enabled=True,
            granularity_policy="single_granularity",
            reranker="metadata_aware",
            final_top_k=5,
            weights={"bm25": 0.75, "negation": 0.15, "numeric": 0.1},
            requires_optional_model=False,
            active=True,
            complexity_rank=3,
        ),
        RetrievalConfiguration(
            configuration_id="cross_granularity_hybrid_v1",
            name="Cross-granularity hybrid",
            candidate_strategy="hybrid",
            candidate_top_k=12,
            embedding_provider="deterministic_hash",
            query_expansion_enabled=True,
            negation_features_enabled=True,
            numeric_features_enabled=True,
            abbreviation_expansion_enabled=True,
            section_aliases_enabled=True,
            granularity_policy="parallel_granularity",
            reranker="metadata_aware",
            final_top_k=5,
            weights={"bm25": 0.55, "hash_dense": 0.2, "metadata": 0.1, "features": 0.15},
            requires_optional_model=False,
            active=True,
            complexity_rank=4,
        ),
        RetrievalConfiguration(
            configuration_id="feature_reranked_hybrid_v1",
            name="Feature-reranked hybrid",
            candidate_strategy="hybrid",
            candidate_top_k=15,
            embedding_provider="deterministic_hash",
            query_expansion_enabled=True,
            negation_features_enabled=True,
            numeric_features_enabled=True,
            abbreviation_expansion_enabled=True,
            section_aliases_enabled=True,
            granularity_policy="hierarchical",
            reranker="feature_weighted",
            final_top_k=5,
            weights={
                "bm25": 0.45,
                "hash_dense": 0.15,
                "metadata": 0.1,
                "negation": 0.1,
                "numeric": 0.1,
                "granularity": 0.1,
            },
            requires_optional_model=False,
            active=True,
            complexity_rank=5,
        ),
        RetrievalConfiguration(
            configuration_id="local_sentence_transformer_hybrid_v1",
            name="Optional local sentence-transformer hybrid",
            candidate_strategy="hybrid",
            candidate_top_k=15,
            embedding_provider="sentence_transformer",
            query_expansion_enabled=True,
            negation_features_enabled=True,
            numeric_features_enabled=True,
            abbreviation_expansion_enabled=True,
            section_aliases_enabled=True,
            granularity_policy="parallel_granularity",
            reranker="feature_weighted",
            final_top_k=5,
            weights={"bm25": 0.35, "local_dense": 0.35, "features": 0.3},
            requires_optional_model=True,
            active=True,
            complexity_rank=6,
        ),
    ]


def write_default_registry(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "configuration_registry_version": CONFIGURATION_REGISTRY_VERSION,
        "configurations": [config.model_dump(mode="json") for config in default_configurations()],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    return path


def load_registry(path: Path | None = None) -> list[RetrievalConfiguration]:
    if path is None or not path.exists():
        return default_configurations()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        RetrievalConfiguration.model_validate(item) for item in loaded.get("configurations", [])
    ]


def write_registry_json(path: Path) -> Path:
    payload = {
        "configuration_registry_version": CONFIGURATION_REGISTRY_VERSION,
        "configurations": [config.model_dump(mode="json") for config in default_configurations()],
    }
    write_json(path, payload)
    return path
