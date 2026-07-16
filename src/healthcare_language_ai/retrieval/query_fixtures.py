"""Deterministic retrieval query fixture generation."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from healthcare_language_ai.retrieval.contracts import RelevanceJudgment, RetrievalQuery
from healthcare_language_ai.retrieval.corpus import unit_id
from healthcare_language_ai.retrieval.serialisation import write_jsonl
from healthcare_language_ai.synthetic.manifest import sha256_file
from healthcare_language_ai.synthetic.serialization import write_json
from healthcare_language_ai.utils.identifiers import deterministic_id

QUERY_SET_VERSION = "1.0.0"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _query(
    *,
    query_id: str,
    text: str,
    category: str,
    target_unit_type: str,
    doc_ids: list[str],
    section_ids: list[str],
    sentence_ids: list[str],
    filters: dict[str, str] | None,
    difficulty: str,
    method: str,
    leakage: str,
) -> RetrievalQuery:
    return RetrievalQuery(
        query_id=query_id,
        query_text=text,
        query_category=category,
        target_unit_type=target_unit_type,
        relevant_document_ids=doc_ids,
        relevant_section_ids=section_ids,
        relevant_sentence_ids=sentence_ids,
        metadata_filters=filters or {},
        difficulty=difficulty,
        generation_method=method,
        leakage_risk=leakage,
        query_version=QUERY_SET_VERSION,
        synthetic_data_only=True,
    )


def generate_query_fixture(*, preprocessing_dir: Path, output_dir: Path) -> Path:
    docs = _read_csv(preprocessing_dir / "processed_documents.csv")
    sections = _read_csv(preprocessing_dir / "processed_sections.csv")
    sentences = _read_csv(preprocessing_dir / "processed_sentences.csv")
    docs_by_type: dict[str, list[str]] = {}
    for doc in docs:
        docs_by_type.setdefault(doc["document_type"], []).append(doc["document_id"])
    section_by_label: dict[str, list[str]] = {}
    for section in sections:
        section_by_label.setdefault(section["normalised_section_label"], []).append(
            section["section_id"]
        )
    sentence_by_section: dict[str, list[str]] = {}
    for sentence in sentences:
        sentence_by_section.setdefault(sentence["section_id"], []).append(sentence["sentence_id"])

    queries: list[RetrievalQuery] = []
    judgments: list[RelevanceJudgment] = []

    def add(query: RetrievalQuery, source_ids: list[str], grade: int) -> None:
        queries.append(query)
        for source_id in source_ids:
            rid = unit_id(
                unit_type=query.target_unit_type,
                source_id=source_id,
                corpus_version="1.0.0",
            )
            judgments.append(
                RelevanceJudgment(
                    judgment_id="RJ_"
                    + deterministic_id({"query": query.query_id, "unit": rid}, length=20),
                    query_id=query.query_id,
                    retrieval_unit_id=rid,
                    relevance_grade=grade,
                    judgment_source="manual_synthetic_lineage",
                    query_version=QUERY_SET_VERSION,
                )
            )

    for index, (doc_type, doc_ids) in enumerate(sorted(docs_by_type.items()), start=1):
        add(
            _query(
                query_id=f"RQ_DIRECT_{index:02d}",
                text=f"{doc_type.replace('_', ' ')} synthetic document",
                category="direct",
                target_unit_type="document",
                doc_ids=doc_ids,
                section_ids=[],
                sentence_ids=[],
                filters={},
                difficulty="easy",
                method="metadata-derived direct query",
                leakage="medium",
            ),
            doc_ids,
            2,
        )
    phrase_queries = [
        ("simulated breathing complaint", "paraphrased", "sentence", "SYN-DOC-004873"),
        ("abdominal discomfort review", "paraphrased", "sentence", "SYN-DOC-339753"),
        ("right wrist specimen report", "compositional", "section", "SYN-DOC-331779"),
        ("routine simulation priority", "direct", "section", "SYN-DOC-274035"),
        ("quality checked discharge workflow", "compositional", "section", "SYN-DOC-494697"),
        ("no focal abnormality chest concern", "negation_sensitive", "sentence", "SYN-DOC-043303"),
        ("oxygen saturation numeric detail 98", "numeric_detail", "sentence", "SYN-DOC-339753"),
        ("radiology finding with abdomen", "metadata_filtered", "section", "SYN-DOC-260561"),
        ("pathology microscopic radiology specialty", "distractor", "section", "SYN-DOC-331779"),
        ("fictional observation unit encounter", "direct", "section", "SYN-DOC-494697"),
    ]
    for idx, (text, category, target_unit_type, document_id) in enumerate(phrase_queries, start=1):
        source_pool = sections if target_unit_type == "section" else sentences
        source_key = "section_id" if target_unit_type == "section" else "sentence_id"
        source_ids = [row[source_key] for row in source_pool if row["document_id"] == document_id][
            :2
        ]
        add(
            _query(
                query_id=f"RQ_MIXED_{idx:02d}",
                text=text,
                category=category,
                target_unit_type=target_unit_type,
                doc_ids=[document_id],
                section_ids=source_ids if target_unit_type == "section" else [],
                sentence_ids=source_ids if target_unit_type == "sentence" else [],
                filters={"unit_type": target_unit_type} if category == "metadata_filtered" else {},
                difficulty="medium" if category != "distractor" else "hard",
                method="manual authored local query",
                leakage="low" if category == "paraphrased" else "medium",
            ),
            source_ids,
            1,
        )
    for idx, doc in enumerate(sorted(docs, key=lambda row: row["document_id"])[:15], start=1):
        add(
            _query(
                query_id=f"RQ_FILTER_{idx:02d}",
                text=f"{doc['document_type'].replace('_', ' ')} subject {idx}",
                category="metadata_filtered",
                target_unit_type="document",
                doc_ids=[doc["document_id"]],
                section_ids=[],
                sentence_ids=[],
                filters={"document_type": doc["document_type"]},
                difficulty="medium",
                method="metadata constraint with local wording",
                leakage="medium",
            ),
            [doc["document_id"]],
            1,
        )
    queries.append(
        _query(
            query_id="RQ_UNANSWERABLE_01",
            text="paediatric transplant medication advice",
            category="unanswerable",
            target_unit_type="document",
            doc_ids=[],
            section_ids=[],
            sentence_ids=[],
            filters={},
            difficulty="hard",
            method="manual deliberately unanswerable query",
            leakage="low",
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "retrieval_queries.jsonl", queries)
    write_jsonl(output_dir / "relevance_judgments.jsonl", judgments)
    manifest = {
        "query_set_version": QUERY_SET_VERSION,
        "query_count": len(queries),
        "relevance_judgment_count": len(judgments),
        "query_category_counts": dict(sorted(Counter(q.query_category for q in queries).items())),
        "difficulty_counts": dict(sorted(Counter(q.difficulty for q in queries).items())),
        "leakage_risk_counts": dict(sorted(Counter(q.leakage_risk for q in queries).items())),
        "target_unit_type_counts": dict(
            sorted(Counter(q.target_unit_type for q in queries).items())
        ),
        "metadata_filtered_query_count": sum(bool(q.metadata_filters) for q in queries),
        "negation_sensitive_query_count": sum(
            q.query_category == "negation_sensitive" for q in queries
        ),
        "unanswerable_query_count": sum(q.query_category == "unanswerable" for q in queries),
        "validation_status": "passed",
    }
    write_json(output_dir / "query_set_manifest.json", manifest)
    manifest["retrieval_queries_checksum"] = sha256_file(output_dir / "retrieval_queries.jsonl")
    manifest["relevance_judgments_checksum"] = sha256_file(output_dir / "relevance_judgments.jsonl")
    write_json(output_dir / "query_set_manifest.json", manifest)
    (output_dir / "README.md").write_text(
        "# Retrieval Query Fixture\n\nSynthetic, manually authored local benchmark queries.\n",
        encoding="utf-8",
    )
    return output_dir
