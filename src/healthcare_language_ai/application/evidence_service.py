"""Read-only indexes over approved fixture-backed RAG evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from healthcare_language_ai.application.contracts import (
    AnswerResponse,
    CitationResponse,
    CitationSummary,
    EvidenceResponse,
    QueryResponse,
)
from healthcare_language_ai.rag.contracts import (
    EvidenceBundle,
    EvidenceUnit,
    RagAnswer,
    RagManifest,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


class EvidenceService:
    """Expose bounded, read-only views of canonical RAG fixture artifacts."""

    def __init__(self, rag_run_dir: Path, rag_query_dir: Path) -> None:
        self.rag_run_dir = rag_run_dir
        self.rag_query_dir = rag_query_dir
        self.manifest = RagManifest.model_validate_json(
            (rag_run_dir / "rag_manifest.json").read_text()
        )
        self.answers = [
            RagAnswer.model_validate(row) for row in _read_jsonl(rag_run_dir / "rag_answers.jsonl")
        ]
        self.answer_by_id = {answer.answer_id: answer for answer in self.answers}
        self.answer_by_query_id = {answer.query_id: answer for answer in self.answers}
        self.bundles = [
            EvidenceBundle.model_validate(row)
            for row in _read_jsonl(rag_run_dir / "evidence_bundles.jsonl")
        ]
        self.bundle_by_query_id = {bundle.query_id: bundle for bundle in self.bundles}
        self.evidence_by_id: dict[str, EvidenceUnit] = {}
        for bundle in self.bundles:
            for unit in bundle.evidence_units:
                self.evidence_by_id[unit.evidence_id] = unit
        self.citation_by_id = {
            citation.citation_id: citation
            for answer in self.answers
            for citation in answer.citations
        }
        self.answer_by_citation_id = {
            citation.citation_id: answer for answer in self.answers for citation in answer.citations
        }
        self.queries = _read_jsonl(rag_query_dir / "rag_queries.jsonl")
        self.query_by_id = {str(row["query_id"]): row for row in self.queries}

    def answer_response(self, answer_id: str, request_id: str = "lookup") -> AnswerResponse:
        answer = self.answer_by_id[answer_id]
        base = self.query_response(answer, request_id=request_id)
        return AnswerResponse(
            **base.model_dump(),
            rag_run_id=answer.rag_run_id,
            prompt_id=answer.prompt_id,
            prompt_version=answer.prompt_version,
            generator_provider=answer.generator_provider,
            generator_version=answer.generator_version,
        )

    def query_response(self, answer: RagAnswer, request_id: str) -> QueryResponse:
        return QueryResponse(
            request_id=request_id,
            query_id=answer.query_id,
            answer_id=answer.answer_id,
            answer_status=answer.answer_status,
            answer_text=answer.answer_text,
            citations=[
                CitationSummary(
                    citation_id=citation.citation_id,
                    citation_label=citation.citation_label,
                    evidence_id=citation.evidence_id,
                    document_id=citation.document_id,
                    section_id=citation.section_id,
                    sentence_id=citation.sentence_id,
                    claim_ids=citation.claim_ids,
                    citation_status=citation.citation_status,
                    quoted_span=citation.quoted_span[:160],
                    source_text_checksum=citation.source_text_checksum,
                )
                for citation in answer.citations
            ],
            retrieval_status=answer.retrieval_status,
            retrieval_confidence=answer.retrieval_confidence,
            trace_id=answer.answer_id,
        )

    def evidence_response(self, evidence_id: str) -> EvidenceResponse:
        unit = self.evidence_by_id[evidence_id]
        return EvidenceResponse(
            evidence_id=unit.evidence_id,
            retrieval_unit_id=unit.retrieval_unit_id,
            document_id=unit.document_id,
            section_id=unit.section_id,
            sentence_id=unit.sentence_id,
            unit_type=unit.unit_type,
            rank=unit.rank,
            retrieval_score=unit.retrieval_score,
            retrieval_confidence=unit.retrieval_confidence,
            bounded_snippet=unit.bounded_snippet[:240],
            text_checksum=unit.text_checksum,
            source_preprocessing_run_id=unit.source_preprocessing_run_id,
            source_extraction_run_id=unit.source_extraction_run_id,
            source_index_id=unit.source_index_id,
        )

    def citation_response(self, citation_id: str) -> CitationResponse:
        citation = self.citation_by_id[citation_id]
        bounded = citation.quoted_span[:160]
        return CitationResponse(
            citation_id=citation.citation_id,
            citation_label=citation.citation_label,
            evidence_id=citation.evidence_id,
            document_id=citation.document_id,
            section_id=citation.section_id,
            sentence_id=citation.sentence_id,
            claim_ids=citation.claim_ids,
            citation_status=citation.citation_status,
            quoted_span=bounded,
            source_text_checksum=citation.source_text_checksum,
            bounded_text=bounded,
        )
