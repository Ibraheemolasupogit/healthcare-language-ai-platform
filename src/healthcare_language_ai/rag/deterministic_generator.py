"""Deterministic model-free RAG generator."""

from __future__ import annotations

from datetime import datetime

from healthcare_language_ai.rag.citations import citation_for_unit
from healthcare_language_ai.rag.contracts import (
    EvidenceBundle,
    GenerationConfiguration,
    RagAnswer,
    RagClaim,
    RagQuery,
)
from healthcare_language_ai.rag.refusals import refusal_text
from healthcare_language_ai.retrieval_quality.io import checksum_text, stable_id

GENERATOR_VERSION = "1.0.0"


def deterministic_config() -> GenerationConfiguration:
    return GenerationConfiguration(
        provider_name="deterministic_extract",
        provider_version=GENERATOR_VERSION,
        model_name="template-extractor",
        generation_mode="deterministic_extract",
        temperature=0.0,
        top_p=1.0,
        seed=9026,
    )


def generate_answer(
    *,
    rag_run_id: str,
    query: RagQuery,
    bundle: EvidenceBundle,
    prompt_id: str,
    prompt_version: str,
    created_at: datetime,
) -> RagAnswer:
    config = deterministic_config()
    if (
        query.expected_answer_status
        in {
            "insufficient_evidence",
            "retrieval_abstention",
            "unanswerable_query",
        }
        or not bundle.evidence_units
    ):
        return _refusal_answer(
            rag_run_id=rag_run_id,
            query=query,
            bundle=bundle,
            reason="retrieval_abstention"
            if bundle.retrieval_status == "query_unanswerable"
            else "unanswerable_query",
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            created_at=created_at,
            config=config,
        )
    if query.expected_answer_status == "conflicting_evidence":
        text = (
            "The retrieved synthetic evidence contains conflicting statements and this "
            "prototype does not choose a clinical conclusion."
        )
        status = "conflicting_evidence"
    else:
        text = (
            "The retrieved synthetic records indicate: "
            f"{bundle.evidence_units[0].bounded_snippet[:180]} "
            f"{bundle.evidence_units[0].citation_label}"
        )
        status = "grounded_answer"
    claim_id = stable_id("CLM", [rag_run_id, query.query_id, text], length=16)
    claim = RagClaim(
        claim_id=claim_id,
        claim_text=text,
        claim_type="factual",
        sentence_index=0,
        support_status="supported",
    )
    citations = [
        citation_for_unit(
            answer_id=stable_id("ANS", [rag_run_id, query.query_id, bundle.context_checksum, text]),
            query_id=query.query_id,
            claim_id=claim_id,
            unit=unit,
        )
        for unit in bundle.evidence_units[: (2 if status == "conflicting_evidence" else 1)]
    ]
    claim.supporting_citation_ids = [citation.citation_id for citation in citations]
    answer_id = stable_id(
        "ANS",
        [rag_run_id, query.query_id, bundle.context_checksum, checksum_text(text)],
    )
    return RagAnswer(
        answer_id=answer_id,
        rag_run_id=rag_run_id,
        query_id=query.query_id,
        answer_status=status,
        answer_text=text,
        answer_text_checksum=checksum_text(text),
        citations=citations,
        claims=[claim],
        refusal_reason="",
        retrieval_status=bundle.retrieval_status,
        retrieval_confidence=bundle.retrieval_confidence,
        generator_provider=config.provider_name,
        generator_version=config.provider_version,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        created_at=created_at,
    )


def _refusal_answer(
    *,
    rag_run_id: str,
    query: RagQuery,
    bundle: EvidenceBundle,
    reason: str,
    prompt_id: str,
    prompt_version: str,
    created_at: datetime,
    config: GenerationConfiguration,
) -> RagAnswer:
    text = refusal_text(reason)
    answer_id = stable_id(
        "ANS", [rag_run_id, query.query_id, bundle.context_checksum, checksum_text(text)]
    )
    return RagAnswer(
        answer_id=answer_id,
        rag_run_id=rag_run_id,
        query_id=query.query_id,
        answer_status="retrieval_abstention"
        if reason == "retrieval_abstention"
        else "unanswerable_query",
        answer_text=text,
        answer_text_checksum=checksum_text(text),
        citations=[],
        claims=[],
        refusal_reason=reason,
        retrieval_status=bundle.retrieval_status,
        retrieval_confidence=bundle.retrieval_confidence,
        generator_provider=config.provider_name,
        generator_version=config.provider_version,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        created_at=created_at,
    )


class InjectedTestGenerator:
    """Small test double used to simulate unsafe or malformed generator output."""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def generate(self) -> str:
        if self.mode == "error":
            raise RuntimeError("deterministic injected generator error")
        return {
            "unsupported_claim": "The synthetic evidence proves an unsupported fact. [E1]",
            "invalid_citation": "The synthetic evidence states a fact. [E99]",
            "no_citations": "The synthetic evidence states a fact.",
            "prohibited": "You should take a medication dosage.",
            "malformed": "{not-json",
        }.get(self.mode, "The synthetic evidence states a fact. [E1]")
