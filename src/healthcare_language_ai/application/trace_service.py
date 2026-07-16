"""Trace views for approved RAG answers."""

from __future__ import annotations

import json
from typing import Any

from healthcare_language_ai.application.contracts import TraceResponse
from healthcare_language_ai.application.evidence_service import EvidenceService, _read_jsonl


class TraceService:
    def __init__(self, evidence: EvidenceService) -> None:
        self.evidence = evidence
        self.citation_validation = {
            row["answer_id"]: row
            for row in _read_jsonl(evidence.rag_run_dir / "citation_validation.jsonl")
        }
        self.groundedness = {
            row["answer_id"]: row
            for row in _read_jsonl(evidence.rag_run_dir / "groundedness_reports.jsonl")
        }
        self.safety = {
            row["answer_id"]: row
            for row in _read_jsonl(evidence.rag_run_dir / "safety_validation.jsonl")
        }
        self.query_safety = {
            row["query_id"]: row for row in _read_jsonl(evidence.rag_run_dir / "query_safety.jsonl")
        }
        self.prompt_records: list[dict[str, Any]] = _read_jsonl(
            evidence.rag_run_dir / "prompt_records.jsonl"
        )

    def get_trace(self, answer_id: str) -> TraceResponse:
        answer = self.evidence.answer_by_id[answer_id]
        bundle = self.evidence.bundle_by_query_id[answer.query_id]
        query = self.evidence.query_by_id.get(answer.query_id, {})
        citation = self.citation_validation.get(answer.answer_id, {})
        grounding = self.groundedness.get(answer.answer_id, {})
        safety = self.safety.get(answer.answer_id, {})
        return TraceResponse(
            trace_id=answer.answer_id,
            answer_id=answer.answer_id,
            query_id=answer.query_id,
            query_category=str(query.get("query_category", "unknown")),
            answer_status=answer.answer_status,
            retrieval_status=answer.retrieval_status,
            retrieval_configuration_id=bundle.retrieval_configuration_id,
            retrieval_approval_id=bundle.retrieval_approval_id,
            retrieval_confidence=answer.retrieval_confidence,
            selected_evidence_ids=[unit.evidence_id for unit in bundle.evidence_units],
            excluded_retrieval_unit_ids=[unit.retrieval_unit_id for unit in bundle.excluded_units],
            prompt_id=answer.prompt_id,
            prompt_version=answer.prompt_version,
            generator_provider=answer.generator_provider,
            generator_version=answer.generator_version,
            claim_ids=[claim.claim_id for claim in answer.claims],
            citation_ids=[citation.citation_id for citation in answer.citations],
            citation_validation_status=str(
                citation.get("citation_validity_status", "not_applicable")
            ),
            groundedness_status=str(grounding.get("groundedness_status", "not_applicable")),
            safety_status=str(safety.get("safety_status", "not_applicable")),
        )

    def to_json(self, answer_id: str) -> str:
        return json.dumps(self.get_trace(answer_id).model_dump(mode="json"), sort_keys=True)
