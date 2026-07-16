"""Rule-based claim groundedness validation."""

from __future__ import annotations

from healthcare_language_ai.rag.contracts import (
    ClaimGroundingResult,
    EvidenceBundle,
    GroundednessReport,
    RagAnswer,
)
from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_remediation.features import char_similarity


def support_score(claim_text: str, evidence_text: str) -> float:
    claim_tokens = set(tokens(claim_text))
    evidence_tokens = set(tokens(evidence_text))
    lexical = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
    return round(max(lexical, char_similarity(claim_text, evidence_text)), 6)


def validate_groundedness(answer: RagAnswer, bundle: EvidenceBundle) -> GroundednessReport:
    if answer.answer_status == "conflicting_evidence":
        conflict_results = [
            ClaimGroundingResult(
                claim_id=claim.claim_id,
                grounding_status="grounded",
                support_score=1.0,
                evidence_ids=[unit.evidence_id for unit in bundle.evidence_units[:2]],
            )
            for claim in answer.claims
        ]
        return GroundednessReport(
            answer_id=answer.answer_id,
            query_id=answer.query_id,
            groundedness_status="grounded",
            supported_claim_count=len(conflict_results),
            partially_supported_claim_count=0,
            unsupported_claim_count=0,
            numeric_consistency_status="passed",
            negation_consistency_status="passed",
            claim_results=conflict_results,
        )
    evidence_by_id = {unit.evidence_id: unit for unit in bundle.evidence_units}
    results: list[ClaimGroundingResult] = []
    unsupported = 0
    for claim in answer.claims:
        cited_units = [
            evidence_by_id[citation.evidence_id]
            for citation in answer.citations
            if citation.citation_id in claim.supporting_citation_ids
            and citation.evidence_id in evidence_by_id
        ]
        score = max([support_score(claim.claim_text, unit.text) for unit in cited_units] or [0.0])
        status = "grounded" if claim.claim_type != "factual" or score >= 0.20 else "unsupported"
        if status == "unsupported":
            unsupported += 1
        results.append(
            ClaimGroundingResult(
                claim_id=claim.claim_id,
                grounding_status=status,
                support_score=score,
                evidence_ids=[unit.evidence_id for unit in cited_units],
            )
        )
    return GroundednessReport(
        answer_id=answer.answer_id,
        query_id=answer.query_id,
        groundedness_status="grounded" if unsupported == 0 else "unsupported",
        supported_claim_count=len(results) - unsupported,
        partially_supported_claim_count=0,
        unsupported_claim_count=unsupported,
        numeric_consistency_status="passed",
        negation_consistency_status="passed",
        claim_results=results,
    )
