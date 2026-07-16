"""Evidence selection from the approved Milestone 8 retriever."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from healthcare_language_ai.rag.contracts import (
    EvidenceBundle,
    EvidenceExclusion,
    EvidenceUnit,
    RagQuery,
)
from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_quality.benchmark import benchmark_units
from healthcare_language_ai.retrieval_quality.io import checksum_text, read_json, stable_id

APPROVED_CONFIGURATION_ID = "abstaining_ensemble_v1"
APPROVED_EXPERIMENT_DIR = Path(
    "tests/fixtures/retrieval-remediation/experiments/REMEXP-41fd5fa127ab616f7f74cc9b"
)
SOURCE_PREPROCESSING_RUN_ID = "PRE-72e9829c61769cea948faacc"
SOURCE_EXTRACTION_RUN_ID = "EXT-723871c87dfd1f3a3bb89b8d"
SOURCE_INDEX_ID = "IDX-364c8b97f9ad74ecea7444a9"


def verify_retrieval_approval(comparison_dir: Path) -> dict[str, str]:
    manifest = read_json(comparison_dir / "comparison_manifest.json")
    if manifest["approval_status"] != "approved_for_rag_prototype":
        raise ValueError("retrieval comparison is not approved for RAG prototype")
    if manifest["selected_configuration_id"] != APPROVED_CONFIGURATION_ID:
        raise ValueError("retrieval comparison selected the wrong configuration")
    if manifest["failed_required_gates"] != 0:
        raise ValueError("retrieval comparison has failed required gates")
    if not (comparison_dir / "retrieval_approval_decision.json").exists():
        raise ValueError("retrieval approval decision is missing")
    return {
        "retrieval_approval_id": manifest["comparison_id"],
        "retrieval_configuration_id": manifest["selected_configuration_id"],
    }


def load_selected_results(
    experiment_dir: Path = APPROVED_EXPERIMENT_DIR,
) -> dict[str, list[dict[str, str]]]:
    with (experiment_dir / "query_results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["query_id"]].append(row)
    return grouped


def assemble_evidence_bundle(
    *,
    rag_run_id: str,
    query: RagQuery,
    retrieval_approval_id: str,
    retrieval_configuration_id: str = APPROVED_CONFIGURATION_ID,
    maximum_evidence_units: int = 5,
    maximum_units_per_document: int = 2,
    maximum_context_characters: int = 6000,
    minimum_retrieval_confidence: float = 0.65,
) -> EvidenceBundle:
    results = load_selected_results()
    unit_lookup = {unit["retrieval_unit_id"]: unit for unit in benchmark_units()}
    rows = sorted(
        results.get(query.source_query_id or query.query_id, []),
        key=lambda row: int(row["rank"] or 999),
    )
    excluded: list[EvidenceExclusion] = []
    selected: list[EvidenceUnit] = []
    per_document: defaultdict[str, int] = defaultdict(int)
    total_chars = 0
    retrieval_status = "no_credible_evidence"
    confidence = 0.0
    for row in rows:
        if row["abstained"] == "True":
            retrieval_status = "query_unanswerable"
            excluded.append(EvidenceExclusion(retrieval_unit_id="", reason="retrieval_abstention"))
            continue
        confidence = max(confidence, float(row["confidence"]))
        unit = unit_lookup.get(row["retrieval_unit_id"])
        if unit is None:
            excluded.append(
                EvidenceExclusion(retrieval_unit_id=row["retrieval_unit_id"], reason="unit_missing")
            )
            continue
        if float(row["confidence"]) < minimum_retrieval_confidence:
            excluded.append(
                EvidenceExclusion(
                    retrieval_unit_id=row["retrieval_unit_id"], reason="low_confidence"
                )
            )
            continue
        if per_document[unit["document_id"]] >= maximum_units_per_document:
            excluded.append(
                EvidenceExclusion(
                    retrieval_unit_id=row["retrieval_unit_id"], reason="document_limit"
                )
            )
            continue
        snippet = unit["text"][: min(700, len(unit["text"]))]
        if total_chars + len(snippet) > maximum_context_characters:
            excluded.append(
                EvidenceExclusion(
                    retrieval_unit_id=row["retrieval_unit_id"], reason="context_limit"
                )
            )
            continue
        evidence_id = stable_id("EVID", [rag_run_id, query.query_id, row["retrieval_unit_id"]])
        selected.append(
            EvidenceUnit(
                evidence_id=evidence_id,
                retrieval_unit_id=row["retrieval_unit_id"],
                document_id=unit["document_id"],
                section_id=unit["section_label"],
                sentence_id="",
                unit_type=unit["unit_type"],
                rank=int(row["rank"]),
                retrieval_score=float(row["score"]),
                retrieval_confidence=float(row["confidence"]),
                text=unit["text"],
                text_checksum=checksum_text(unit["text"]),
                bounded_snippet=snippet,
                source_preprocessing_run_id=SOURCE_PREPROCESSING_RUN_ID,
                source_extraction_run_id=SOURCE_EXTRACTION_RUN_ID,
                source_index_id=SOURCE_INDEX_ID,
                citation_label=f"[E{len(selected) + 1}]",
            )
        )
        per_document[unit["document_id"]] += 1
        total_chars += len(snippet)
        if len(selected) >= maximum_evidence_units:
            break
    if selected:
        retrieval_status = "evidence_selected"
    context_text = "\n".join(f"{unit.citation_label} {unit.bounded_snippet}" for unit in selected)
    return EvidenceBundle(
        evidence_bundle_id=stable_id("EVB", [rag_run_id, query.query_id, context_text]),
        query_id=query.query_id,
        query_text_checksum=checksum_text(query.query_text),
        retrieval_run_id=APPROVED_EXPERIMENT_DIR.name,
        retrieval_configuration_id=retrieval_configuration_id,
        retrieval_approval_id=retrieval_approval_id,
        retrieval_status=retrieval_status,
        retrieval_confidence=round(confidence, 6),
        selected_unit_count=len(selected),
        selected_document_count=len({unit.document_id for unit in selected}),
        selected_section_count=sum(1 for unit in selected if unit.unit_type == "section"),
        selected_sentence_count=sum(1 for unit in selected if unit.unit_type == "sentence"),
        total_character_count=total_chars,
        total_token_count=sum(len(tokens(unit.bounded_snippet)) for unit in selected),
        evidence_units=selected,
        excluded_units=excluded,
        context_checksum=checksum_text(context_text),
    )
