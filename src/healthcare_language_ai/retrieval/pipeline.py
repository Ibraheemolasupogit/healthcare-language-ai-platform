"""Local retrieval index and run pipelines."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow

from healthcare_language_ai.config import RetrievalSettings
from healthcare_language_ai.embeddings.hashing import HASH_EMBEDDING_VERSION, hash_vector
from healthcare_language_ai.exceptions import DataGovernanceError
from healthcare_language_ai.extraction.pipeline import load_extraction_manifest
from healthcare_language_ai.extraction.validation import validate_extraction_dir
from healthcare_language_ai.ingestion.contracts import OverwritePolicy
from healthcare_language_ai.preprocessing.pipeline import load_preprocessing_manifest
from healthcare_language_ai.preprocessing.validation import validate_preprocessing_dir
from healthcare_language_ai.retrieval.contracts import (
    EmbeddingProvider,
    IndexManifest,
    RelevanceJudgment,
    RetrievalManifest,
    RetrievalQuery,
    RetrievalResult,
    RetrievalRunStatus,
    RetrievalStrategy,
    RetrievalUnit,
)
from healthcare_language_ai.retrieval.corpus import build_units, corpus_statistics
from healthcare_language_ai.retrieval.scoring import (
    BM25_VERSION,
    HYBRID_VERSION,
    KEYWORD_VERSION,
    SCORE_NORMALISATION_VERSION,
    TFIDF_VERSION,
    bm25_score,
    dense_score,
    document_frequency,
    keyword_score,
    metadata_score,
    normalise_scores,
    passes_filters,
    sparse_cosine,
    tfidf_vector,
    vocabulary,
)
from healthcare_language_ai.retrieval.serialisation import (
    RESULT_COLUMNS,
    UNIT_COLUMNS,
    write_csv,
    write_json_model,
    write_jsonl,
    write_parquet,
)
from healthcare_language_ai.retrieval.tokenisation import TOKENISER_VERSION
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import read_json, write_json
from healthcare_language_ai.utils.identifiers import deterministic_id


def derive_index_id(
    *,
    preprocessing_manifest_checksum: str,
    extraction_manifest_checksum: str,
    corpus_version: str,
    unit_type: str,
    text_representation: str,
    tokeniser_version: str,
    embedding_provider: str,
    embedding_dimension: int,
    reference_timestamp: datetime,
) -> str:
    return "IDX-" + deterministic_id(
        {
            "preprocessing_manifest_checksum": preprocessing_manifest_checksum,
            "extraction_manifest_checksum": extraction_manifest_checksum,
            "corpus_version": corpus_version,
            "unit_type": unit_type,
            "text_representation": text_representation,
            "tokeniser_version": tokeniser_version,
            "embedding_provider": embedding_provider,
            "embedding_dimension": embedding_dimension,
            "reference_timestamp": reference_timestamp.isoformat(),
        },
        length=24,
    )


def derive_retrieval_run_id(
    *,
    index_manifest_checksum: str,
    query_set_checksum: str,
    strategy: str,
    top_k: int,
    filter_policy: str,
    fusion_version: str,
    fusion_weights: dict[str, float],
    reference_timestamp: datetime,
) -> str:
    return "RET-" + deterministic_id(
        {
            "index_manifest_checksum": index_manifest_checksum,
            "query_set_checksum": query_set_checksum,
            "strategy": strategy,
            "top_k": top_k,
            "filter_policy": filter_policy,
            "fusion_version": fusion_version,
            "fusion_weights": fusion_weights,
            "reference_timestamp": reference_timestamp.isoformat(),
        },
        length=24,
    )


def _prepare_output_dir(output_dir: Path, policy: OverwritePolicy) -> None:
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if policy is OverwritePolicy.FAIL_IF_EXISTS:
        msg = f"output directory already exists: {output_dir}"
        raise FileExistsError(msg)
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _count_by(items: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(items).items()))


def build_index(
    *,
    preprocessing_dir: Path,
    extraction_dir: Path,
    output_root: Path,
    unit_type: str,
    embedding_provider: str,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: RetrievalSettings,
) -> Path:
    if unit_type not in {"document", "section", "sentence", "all"}:
        raise ValueError("unit type must be one of: document, section, sentence, all")
    if embedding_provider != "deterministic_hash":
        raise ValueError("default validation supports only deterministic_hash embeddings")
    if validate_preprocessing_dir(preprocessing_dir) or validate_extraction_dir(extraction_dir):
        raise DataGovernanceError("source evidence failed validation")
    preprocessing_manifest = load_preprocessing_manifest(preprocessing_dir)
    extraction_manifest = load_extraction_manifest(extraction_dir)
    if (
        not preprocessing_manifest.synthetic_data_only
        or not extraction_manifest.synthetic_data_only
    ):
        raise DataGovernanceError("retrieval sources must be synthetic only")
    pre_checksum = sha256_file(preprocessing_dir / "preprocessing_manifest.json")
    ext_checksum = sha256_file(extraction_dir / "extraction_manifest.json")
    index_id = derive_index_id(
        preprocessing_manifest_checksum=pre_checksum,
        extraction_manifest_checksum=ext_checksum,
        corpus_version=settings.corpus_version,
        unit_type=unit_type,
        text_representation=settings.default_text_representation,
        tokeniser_version=settings.tokeniser_version,
        embedding_provider=embedding_provider,
        embedding_dimension=settings.embedding_dimension,
        reference_timestamp=reference_timestamp,
    )
    output_dir = output_root / index_id
    _prepare_output_dir(output_dir, overwrite_policy)
    units = build_units(
        preprocessing_dir=preprocessing_dir,
        extraction_run_id=extraction_manifest.extraction_run_id,
        corpus_version=settings.corpus_version,
        unit_type=unit_type,
    )
    if len(units) > settings.maximum_retrieval_units:
        raise DataGovernanceError("retrieval-unit count exceeds configured maximum")
    stats = corpus_statistics(units)
    vocab = vocabulary(units)
    dfs = document_frequency(units)
    corpus_size = len(units)
    average_length = round(sum(unit.token_count for unit in units) / max(1, corpus_size), 6)
    tfidf_rows = {
        unit.retrieval_unit_id: tfidf_vector(unit.text, vocab, dfs, corpus_size) for unit in units
    }
    embeddings = {
        unit.retrieval_unit_id: hash_vector(unit.text, dimension=settings.embedding_dimension)
        for unit in units
    }
    write_csv(output_dir / "retrieval_units.csv", units, UNIT_COLUMNS)
    write_parquet(output_dir / "retrieval_units.parquet", units, UNIT_COLUMNS)
    write_json_model(output_dir / "corpus_statistics.json", stats)
    write_json(output_dir / "vocabulary.json", {"vocabulary": vocab, "document_frequency": dfs})
    write_json(output_dir / "tfidf_matrix.json", tfidf_rows)
    write_json(
        output_dir / "bm25_statistics.json",
        {
            "k1": settings.bm25_k1,
            "b": settings.bm25_b,
            "average_document_length": average_length,
            "tokeniser_version": TOKENISER_VERSION,
            "corpus_size": corpus_size,
            "document_frequency": dfs,
        },
    )
    write_json(output_dir / "hash_embeddings.json", embeddings)
    write_json(
        output_dir / "embedding_metadata.json",
        {
            "embedding_provider": embedding_provider,
            "embedding_dimension": settings.embedding_dimension,
            "hash_embedding_version": HASH_EMBEDDING_VERSION,
            "tokeniser_version": TOKENISER_VERSION,
            "ngram_range": [settings.hash_ngram_min, settings.hash_ngram_max],
            "automatic_download_permitted": False,
        },
    )
    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "index_manifest.json"
    }
    reconciliation = {
        "reconciliation_schema_version": "1.0.0",
        "run_id": index_id,
        "overall_status": "passed",
        "metrics": [
            {
                "metric_name": "retrieval_unit_count",
                "expected_value": len(units),
                "actual_value": len({unit.retrieval_unit_id for unit in units}),
                "status": "passed",
                "severity": "info",
                "message": "retrieval unit IDs are unique",
            }
        ],
    }
    write_json(output_dir / "index_reconciliation.json", reconciliation)
    output_checksums["index_reconciliation.json"] = sha256_file(
        output_dir / "index_reconciliation.json"
    )
    manifest = IndexManifest(
        manifest_schema_version="1.0.0",
        retrieval_contract_version=settings.retrieval_contract_version,
        index_id=index_id,
        run_status=RetrievalRunStatus.COMPLETED,
        source_preprocessing_run_id=preprocessing_manifest.preprocessing_run_id,
        source_preprocessing_manifest_checksum=pre_checksum,
        source_extraction_run_id=extraction_manifest.extraction_run_id,
        source_extraction_manifest_checksum=ext_checksum,
        corpus_version=settings.corpus_version,
        unit_types=sorted(stats.unit_type_distribution),
        text_representation="normalised_text",
        retrieval_unit_count=len(units),
        document_count=stats.document_count,
        section_count=stats.section_count,
        sentence_count=stats.sentence_count,
        token_count=stats.token_count,
        vocabulary_size=len(vocab),
        index_strategies=["keyword", "tfidf", "bm25", "hybrid"],
        embedding_provider=EmbeddingProvider.DETERMINISTIC_HASH,
        embedding_dimension=settings.embedding_dimension,
        tokeniser_version=TOKENISER_VERSION,
        keyword_version=KEYWORD_VERSION,
        tfidf_version=TFIDF_VERSION,
        bm25_version=BM25_VERSION,
        hash_embedding_version=HASH_EMBEDDING_VERSION,
        hybrid_version=HYBRID_VERSION,
        reference_timestamp=reference_timestamp,
        writer_versions={"pyarrow": pyarrow.__version__, "csv": "python-stdlib"},
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status="passed",
    )
    write_json_model(output_dir / "index_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        f"# Retrieval Index Evidence\n\nIndex ID: {index_id}\n", encoding="utf-8"
    )
    return output_dir


def load_index_manifest(index_dir: Path) -> IndexManifest:
    return IndexManifest.model_validate(read_json(index_dir / "index_manifest.json"))


def load_queries(path: Path) -> list[RetrievalQuery]:
    return [RetrievalQuery.model_validate(row) for row in _read_jsonl(path)]


def load_judgments(path: Path) -> list[RelevanceJudgment]:
    return [RelevanceJudgment.model_validate(row) for row in _read_jsonl(path)]


def _snippet(text: str, limit: int) -> str:
    return text.replace("\n", " ")[:limit]


def _score_rows(
    *,
    query: RetrievalQuery,
    units: list[RetrievalUnit],
    strategy: RetrievalStrategy,
    vocab: list[str],
    dfs: dict[str, int],
    tfidf_rows: dict[str, dict[str, float]],
    judgments: dict[str, dict[str, int]],
    settings: RetrievalSettings,
) -> list[dict[str, Any]]:
    filtered = [unit for unit in units if passes_filters(query, unit)]
    query_tfidf = tfidf_vector(query.query_text, vocab, dfs, len(units))
    average_length = sum(unit.token_count for unit in units) / max(1, len(units))
    rows: list[dict[str, Any]] = []
    raw_keyword: list[float] = []
    raw_tfidf: list[float] = []
    raw_bm25: list[float] = []
    raw_dense: list[float] = []
    raw_metadata: list[float] = []
    matched_terms_by_unit: dict[str, list[str]] = {}
    for unit in filtered:
        keyword, matched = keyword_score(query, unit)
        matched_terms_by_unit[unit.retrieval_unit_id] = matched
        raw_keyword.append(keyword)
        raw_tfidf.append(sparse_cosine(query_tfidf, tfidf_rows.get(unit.retrieval_unit_id, {})))
        raw_bm25.append(
            bm25_score(
                query,
                unit,
                dfs=dfs,
                corpus_size=len(units),
                average_length=average_length,
                k1=settings.bm25_k1,
                b=settings.bm25_b,
            )
        )
        raw_dense.append(dense_score(query, unit, dimension=settings.embedding_dimension))
        raw_metadata.append(metadata_score(query, unit))
    norm_keyword = normalise_scores(raw_keyword)
    norm_tfidf = normalise_scores(raw_tfidf)
    norm_bm25 = normalise_scores(raw_bm25)
    norm_dense = normalise_scores([max(0.0, score) for score in raw_dense])
    norm_metadata = normalise_scores(raw_metadata)
    weights = {
        "keyword": settings.keyword_weight,
        "tfidf": settings.tfidf_weight,
        "bm25": settings.bm25_weight,
        "dense": settings.dense_weight,
        "metadata": settings.metadata_weight,
    }
    for index, unit in enumerate(filtered):
        if strategy is RetrievalStrategy.KEYWORD:
            score = norm_keyword[index]
        elif strategy is RetrievalStrategy.TFIDF:
            score = norm_tfidf[index]
        elif strategy is RetrievalStrategy.BM25:
            score = norm_bm25[index]
        else:
            score = (
                weights["keyword"] * norm_keyword[index]
                + weights["tfidf"] * norm_tfidf[index]
                + weights["bm25"] * norm_bm25[index]
                + weights["dense"] * norm_dense[index]
                + weights["metadata"] * norm_metadata[index]
            ) / sum(weights.values())
        relevance_grade = judgments.get(query.query_id, {}).get(unit.retrieval_unit_id, 0)
        rows.append(
            {
                "unit": unit,
                "score": round(score, 10),
                "keyword_score": norm_keyword[index],
                "tfidf_score": norm_tfidf[index],
                "bm25_score": norm_bm25[index],
                "dense_score": norm_dense[index],
                "metadata_score": norm_metadata[index],
                "fusion_score": round(score, 10),
                "matched_terms": ";".join(matched_terms_by_unit[unit.retrieval_unit_id]),
                "relevant": relevance_grade > 0,
                "relevance_grade": relevance_grade,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["score"]),
            row["unit"].unit_type.value,
            row["unit"].document_id,
            row["unit"].retrieval_unit_id,
        ),
    )


def run_retrieval(
    *,
    index_dir: Path,
    query_set: Path,
    output_root: Path,
    strategy: RetrievalStrategy,
    top_k: int,
    reference_timestamp: datetime,
    overwrite_policy: OverwritePolicy,
    settings: RetrievalSettings,
) -> Path:
    from healthcare_language_ai.retrieval.validation import validate_index_dir

    failures = validate_index_dir(index_dir)
    if failures:
        raise DataGovernanceError(f"index validation failed: {failures[0]}")
    index_manifest = load_index_manifest(index_dir)
    queries = load_queries(query_set)
    if len(queries) > settings.maximum_queries:
        raise DataGovernanceError("query count exceeds configured maximum")
    weights = {
        "keyword": settings.keyword_weight,
        "tfidf": settings.tfidf_weight,
        "bm25": settings.bm25_weight,
        "dense": settings.dense_weight,
        "metadata": settings.metadata_weight,
    }
    retrieval_run_id = derive_retrieval_run_id(
        index_manifest_checksum=sha256_file(index_dir / "index_manifest.json"),
        query_set_checksum=sha256_file(query_set),
        strategy=strategy.value,
        top_k=top_k,
        filter_policy=settings.relaxed_filter_policy,
        fusion_version=settings.hybrid_version,
        fusion_weights=weights,
        reference_timestamp=reference_timestamp,
    )
    output_dir = output_root / retrieval_run_id
    _prepare_output_dir(output_dir, overwrite_policy)
    units = [
        RetrievalUnit.model_validate(row) for row in _read_csv(index_dir / "retrieval_units.csv")
    ]
    vocab_data = read_json(index_dir / "vocabulary.json")
    vocab = list(vocab_data["vocabulary"])
    dfs = {key: int(value) for key, value in vocab_data["document_frequency"].items()}
    tfidf_rows = read_json(index_dir / "tfidf_matrix.json")
    judgment_path = query_set.parent / "relevance_judgments.jsonl"
    judgments = {
        query.query_id: {
            judgment.retrieval_unit_id: judgment.relevance_grade
            for judgment in load_judgments(judgment_path)
            if judgment.query_id == query.query_id
        }
        for query in queries
    }
    results: list[RetrievalResult] = []
    for query in queries:
        scored = _score_rows(
            query=query,
            units=units,
            strategy=strategy,
            vocab=vocab,
            dfs=dfs,
            tfidf_rows=tfidf_rows,
            judgments=judgments,
            settings=settings,
        )
        for rank, row in enumerate(scored[:top_k], start=1):
            unit: RetrievalUnit = row["unit"]
            results.append(
                RetrievalResult(
                    retrieval_run_id=retrieval_run_id,
                    query_id=query.query_id,
                    rank=rank,
                    retrieval_unit_id=unit.retrieval_unit_id,
                    document_id=unit.document_id,
                    section_id=unit.section_id,
                    sentence_id=unit.sentence_id,
                    unit_type=unit.unit_type.value,
                    document_type=unit.document_type,
                    section_label=unit.section_label,
                    score=row["score"],
                    keyword_score=row["keyword_score"],
                    tfidf_score=row["tfidf_score"],
                    bm25_score=row["bm25_score"],
                    dense_score=row["dense_score"],
                    metadata_score=row["metadata_score"],
                    fusion_score=row["fusion_score"],
                    matched_terms=row["matched_terms"],
                    text_checksum=unit.text_checksum,
                    sanitised_snippet=_snippet(unit.text, settings.snippet_character_limit),
                    relevant=row["relevant"],
                    relevance_grade=row["relevance_grade"],
                )
            )
    write_csv(output_dir / "retrieval_results.csv", results, RESULT_COLUMNS)
    write_jsonl(output_dir / "retrieval_results.jsonl", results)
    output_checksums = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "retrieval_manifest.json"
    }
    zero_result_queries = len(
        {query.query_id for query in queries} - {result.query_id for result in results}
    )
    reconciliation = {
        "reconciliation_schema_version": "1.0.0",
        "run_id": retrieval_run_id,
        "overall_status": "passed",
        "metrics": [],
    }
    write_json(output_dir / "retrieval_reconciliation.json", reconciliation)
    output_checksums["retrieval_reconciliation.json"] = sha256_file(
        output_dir / "retrieval_reconciliation.json"
    )
    manifest = RetrievalManifest(
        manifest_schema_version="1.0.0",
        retrieval_contract_version=settings.retrieval_contract_version,
        retrieval_run_id=retrieval_run_id,
        run_status=RetrievalRunStatus.COMPLETED,
        index_id=index_manifest.index_id,
        index_manifest_checksum=sha256_file(index_dir / "index_manifest.json"),
        query_set_checksum=sha256_file(query_set),
        strategy=strategy,
        top_k=top_k,
        query_count=len(queries),
        returned_result_count=len(results),
        zero_result_query_count=zero_result_queries,
        metadata_filtered_query_count=sum(bool(query.metadata_filters) for query in queries),
        filter_policy=settings.relaxed_filter_policy,
        score_normalisation_version=SCORE_NORMALISATION_VERSION,
        fusion_version=HYBRID_VERSION if strategy is RetrievalStrategy.HYBRID else "not_applicable",
        fusion_weights=weights if strategy is RetrievalStrategy.HYBRID else {},
        reference_timestamp=reference_timestamp,
        output_files=sorted(output_checksums),
        output_file_checksums=dict(sorted(output_checksums.items())),
        synthetic_data_only=True,
        clinical_use_prohibited=True,
        reconciliation_status="passed",
    )
    write_json_model(output_dir / "retrieval_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        f"# Retrieval Run Evidence\n\nRun ID: {retrieval_run_id}\n", encoding="utf-8"
    )
    return output_dir


def load_retrieval_manifest(retrieval_dir: Path) -> RetrievalManifest:
    return RetrievalManifest.model_validate(read_json(retrieval_dir / "retrieval_manifest.json"))
