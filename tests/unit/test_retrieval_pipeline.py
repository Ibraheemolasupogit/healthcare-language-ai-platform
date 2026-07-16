from __future__ import annotations

import csv
import filecmp
import json
import math
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import validate

from healthcare_language_ai.config import RetrievalSettings
from healthcare_language_ai.embeddings.hashing import hash_vector
from healthcare_language_ai.embeddings.sentence_transformer import validate_local_model_path
from healthcare_language_ai.evaluation.retrieval_pipeline import evaluate_retrieval
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.retrieval.pipeline import build_index, run_retrieval
from healthcare_language_ai.retrieval.scoring import bm25_score, keyword_score
from healthcare_language_ai.retrieval.tokenisation import ngrams, tokens
from healthcare_language_ai.retrieval.validation import (
    validate_index_dir,
    validate_retrieval_dir,
    validate_retrieval_evaluation_dir,
)

PRE = Path("tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc")
EXT = Path("tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d")
QUERY_DIR = Path("tests/fixtures/retrieval/queries")
INDEX = Path("tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9")
BM25_RUN = Path("tests/fixtures/retrieval/runs/RET-f8cc230a729145594d08b389")
HYBRID_RUN = Path("tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296")
BM25_EVAL = Path("tests/fixtures/retrieval/evaluation/RETEVAL-e7f370442452fb045cd7d541")
HYBRID_EVAL = Path("tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b")


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_tokenisation_preserves_negation_numbers_and_ids() -> None:
    assert tokens("No oxygen 98 percent SYN-DOC-123456.") == [
        "no",
        "oxygen",
        "98",
        "percent",
        "syn-doc-123456",
    ]
    assert ngrams(["no", "oxygen"], ngram_min=1, ngram_max=2) == [
        "no",
        "oxygen",
        "no oxygen",
    ]


def test_hash_embeddings_are_deterministic_and_finite() -> None:
    first = hash_vector("synthetic chest review", dimension=32)
    second = hash_vector("synthetic chest review", dimension=32)
    changed = hash_vector("synthetic abdomen review", dimension=32)
    assert first == second
    assert first != changed
    assert len(first) == 32
    assert all(math.isfinite(value) for value in first)


def test_optional_sentence_transformer_requires_local_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        validate_local_model_path(tmp_path / "missing-model")


def test_index_fixture_counts_and_lineage_validate() -> None:
    manifest = json.loads((INDEX / "index_manifest.json").read_text())
    assert manifest["retrieval_unit_count"] == 153
    assert manifest["document_count"] == 15
    assert manifest["section_count"] == 69
    assert manifest["sentence_count"] == 69
    assert manifest["embedding_provider"] == "deterministic_hash"
    assert validate_index_dir(INDEX) == []


def test_keyword_and_bm25_scores_are_deterministic() -> None:
    from healthcare_language_ai.retrieval.contracts import RetrievalQuery, RetrievalUnit

    unit = RetrievalUnit.model_validate(_csv_rows(INDEX / "retrieval_units.csv")[0])
    query = RetrievalQuery.model_validate(
        json.loads((QUERY_DIR / "retrieval_queries.jsonl").read_text().splitlines()[0])
    )
    first, matched = keyword_score(query, unit)
    second, _ = keyword_score(query, unit)
    assert first == second
    assert isinstance(matched, list)
    assert (
        bm25_score(
            query,
            unit,
            dfs={"synthetic": 10},
            corpus_size=153,
            average_length=10,
            k1=1.5,
            b=0.75,
        )
        >= 0
    )


def test_index_fixture_is_reproducible(tmp_path: Path) -> None:
    generated = build_index(
        preprocessing_dir=PRE,
        extraction_dir=EXT,
        output_root=tmp_path,
        unit_type="all",
        embedding_provider="deterministic_hash",
        reference_timestamp=datetime.fromisoformat("2026-01-06T09:00:00+00:00"),
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=RetrievalSettings(),
    )
    assert filecmp.cmp(
        INDEX / "index_manifest.json", generated / "index_manifest.json", shallow=False
    )


def test_retrieval_runs_and_evaluations_validate() -> None:
    assert validate_retrieval_dir(BM25_RUN) == []
    assert validate_retrieval_dir(HYBRID_RUN) == []
    assert validate_retrieval_evaluation_dir(BM25_EVAL) == []
    assert validate_retrieval_evaluation_dir(HYBRID_EVAL) == []


def test_hybrid_retrieval_fixture_is_reproducible(tmp_path: Path) -> None:
    generated = run_retrieval(
        index_dir=INDEX,
        query_set=QUERY_DIR / "retrieval_queries.jsonl",
        output_root=tmp_path,
        strategy=__import__(
            "healthcare_language_ai.retrieval.contracts", fromlist=["RetrievalStrategy"]
        ).RetrievalStrategy.HYBRID,
        top_k=5,
        reference_timestamp=datetime.fromisoformat("2026-01-07T09:00:00+00:00"),
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=RetrievalSettings(),
    )
    assert filecmp.cmp(
        HYBRID_RUN / "retrieval_manifest.json",
        generated / "retrieval_manifest.json",
        shallow=False,
    )


def test_retrieval_evaluation_fixture_is_reproducible(tmp_path: Path) -> None:
    generated = evaluate_retrieval(
        retrieval_dir=HYBRID_RUN,
        relevance_judgments=QUERY_DIR / "relevance_judgments.jsonl",
        output_root=tmp_path,
        k_values=[1, 3, 5, 10],
        reference_timestamp=datetime.fromisoformat("2026-01-08T09:00:00+00:00"),
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=RetrievalSettings(),
    )
    assert filecmp.cmp(
        HYBRID_EVAL / "retrieval_evaluation_manifest.json",
        generated / "retrieval_evaluation_manifest.json",
        shallow=False,
    )


def test_query_fixture_manifest_and_schema_validation() -> None:
    manifest = json.loads((QUERY_DIR / "query_set_manifest.json").read_text())
    assert manifest["query_count"] == 31
    assert manifest["unanswerable_query_count"] == 1
    assert manifest["metadata_filtered_query_count"] == 16
    validate(
        json.loads((INDEX / "index_manifest.json").read_text()),
        json.loads(Path("schemas/retrieval/index-manifest.schema.json").read_text()),
    )
    validate(
        json.loads((HYBRID_EVAL / "retrieval_evaluation_manifest.json").read_text()),
        json.loads(Path("schemas/retrieval/retrieval-evaluation-manifest.schema.json").read_text()),
    )


def test_tampered_index_fails_validation(tmp_path: Path) -> None:
    generated = build_index(
        preprocessing_dir=PRE,
        extraction_dir=EXT,
        output_root=tmp_path,
        unit_type="all",
        embedding_provider="deterministic_hash",
        reference_timestamp=datetime.fromisoformat("2026-01-06T09:00:00+00:00"),
        overwrite_policy=OverwritePolicy.FORCE_REPLACE,
        settings=RetrievalSettings(),
    )
    with (generated / "retrieval_units.csv").open("a", encoding="utf-8") as stream:
        stream.write("\n")
    assert validate_index_dir(generated)
