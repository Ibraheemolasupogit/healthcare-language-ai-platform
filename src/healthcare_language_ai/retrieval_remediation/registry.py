"""Remediation configuration registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from healthcare_language_ai.retrieval_quality.io import write_json
from healthcare_language_ai.retrieval_remediation.contracts import RemediationConfiguration


def default_configurations() -> list[RemediationConfiguration]:
    rows = [
        (
            "char_tfidf_v1",
            ["char_tfidf"],
            ["char_3_5"],
            [],
            [],
            False,
            False,
            [],
            "none",
            False,
            False,
        ),
        (
            "word_char_hybrid_v1",
            ["bm25", "char_tfidf"],
            ["char_3_5"],
            [],
            [],
            False,
            False,
            [],
            "rrf",
            False,
            False,
        ),
        (
            "phrase_proximity_bm25_v1",
            ["bm25"],
            [],
            ["ordered_bigram"],
            ["window_span"],
            False,
            False,
            [],
            "none",
            False,
            False,
        ),
        (
            "field_aware_bm25_v1",
            ["field_bm25"],
            [],
            [],
            [],
            False,
            False,
            ["document_type", "section_label"],
            "none",
            False,
            False,
        ),
        (
            "entity_enriched_hybrid_v1",
            ["bm25", "entity"],
            [],
            [],
            [],
            True,
            False,
            ["clinical_concept"],
            "rrf",
            False,
            False,
        ),
        (
            "pseudo_feedback_bm25_v1",
            ["bm25", "prf"],
            [],
            [],
            [],
            True,
            True,
            [],
            "none",
            False,
            False,
        ),
        (
            "multi_retriever_rrf_v1",
            ["bm25", "char_tfidf", "field_bm25", "entity"],
            ["char_3_5"],
            ["ordered_bigram"],
            ["window_span"],
            True,
            False,
            ["clinical_concept"],
            "rrf",
            False,
            False,
        ),
        (
            "advanced_feature_reranked_v1",
            ["bm25", "char_tfidf", "field_bm25", "entity"],
            ["char_3_5"],
            ["ordered_bigram"],
            ["window_span"],
            True,
            True,
            ["clinical_concept", "numeric", "negation"],
            "feature_reranker",
            False,
            False,
        ),
        (
            "diversified_ensemble_v1",
            ["bm25", "char_tfidf", "field_bm25", "entity"],
            ["char_3_5"],
            ["ordered_bigram"],
            ["window_span"],
            True,
            True,
            ["clinical_concept", "numeric", "negation"],
            "feature_reranker",
            True,
            False,
        ),
        (
            "abstaining_ensemble_v1",
            ["bm25", "char_tfidf", "field_bm25", "entity"],
            ["char_3_5"],
            ["ordered_bigram"],
            ["window_span"],
            True,
            True,
            ["clinical_concept", "numeric", "negation"],
            "feature_reranker",
            True,
            True,
        ),
    ]
    return [
        RemediationConfiguration(
            configuration_id=row[0],
            candidate_retrievers=row[1],
            character_features=row[2],
            phrase_features=row[3],
            proximity_features=row[4],
            synonym_expansion=row[5],
            pseudo_relevance_feedback=row[6],
            entity_features=row[7],
            reranker=row[8],
            diversification=row[9],
            abstention=row[10],
            description=f"Milestone 8 model-free remediation configuration {row[0]}.",
        )
        for row in rows
    ]


def load_registry(path: Path | None = None) -> list[RemediationConfiguration]:
    if path is None:
        return default_configurations()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    configs: list[dict[str, Any]] = loaded["configurations"] if isinstance(loaded, dict) else loaded
    return [RemediationConfiguration.model_validate(config) for config in configs]


def write_default_registry(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    configs = [config.model_dump(mode="json") for config in default_configurations()]
    path.write_text(yaml.safe_dump({"configurations": configs}, sort_keys=False), encoding="utf-8")
    return path


def write_registry_json(path: Path) -> None:
    write_json(
        path, {"configurations": [c.model_dump(mode="json") for c in default_configurations()]}
    )
