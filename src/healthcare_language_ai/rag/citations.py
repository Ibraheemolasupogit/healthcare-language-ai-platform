"""Citation validation and bounded deterministic repair."""

from __future__ import annotations

from healthcare_language_ai.rag.contracts import (
    CitationValidationResult,
    EvidenceBundle,
    EvidenceUnit,
    RagAnswer,
    RagCitation,
)


def repair_citations(answer: RagAnswer, bundle: EvidenceBundle) -> RagAnswer:
    labels = {unit.citation_label: unit for unit in bundle.evidence_units}
    repaired = []
    seen: set[str] = set()
    for citation in answer.citations:
        label = citation.citation_label.strip()
        if label in labels and citation.citation_id not in seen:
            unit = labels[label]
            repaired.append(
                citation.model_copy(
                    update={
                        "evidence_id": unit.evidence_id,
                        "retrieval_unit_id": unit.retrieval_unit_id,
                        "document_id": unit.document_id,
                        "source_text_checksum": unit.text_checksum,
                    }
                )
            )
            seen.add(citation.citation_id)
    return answer.model_copy(update={"citations": repaired})


def validate_citations(answer: RagAnswer, bundle: EvidenceBundle) -> CitationValidationResult:
    evidence_by_id = {unit.evidence_id: unit for unit in bundle.evidence_units}
    labels = [citation.citation_label for citation in answer.citations]
    invalid = 0
    for citation in answer.citations:
        unit = evidence_by_id.get(citation.evidence_id)
        if unit is None:
            invalid += 1
            continue
        if citation.citation_label != unit.citation_label:
            invalid += 1
        if citation.quoted_span not in unit.text:
            invalid += 1
        if citation.quoted_span_start < 0 or citation.quoted_span_end > len(unit.text):
            invalid += 1
        if citation.citation_label in [
            excluded.retrieval_unit_id for excluded in bundle.excluded_units
        ]:
            invalid += 1
    claims_with = sum(1 for claim in answer.claims if claim.supporting_citation_ids)
    claims_without = sum(
        1
        for claim in answer.claims
        if claim.claim_type == "factual" and not claim.supporting_citation_ids
    )
    if len(labels) != len(set(labels)):
        invalid += 1
    status = "passed" if invalid == 0 and claims_without == 0 else "failed"
    return CitationValidationResult(
        answer_id=answer.answer_id,
        query_id=answer.query_id,
        citation_validity_status=status,
        invalid_citation_count=invalid,
        claims_with_citations=claims_with,
        claims_without_citations=claims_without,
    )


def citation_for_unit(
    *,
    answer_id: str,
    query_id: str,
    claim_id: str,
    unit: EvidenceUnit,
) -> RagCitation:
    quote = unit.bounded_snippet[:120]
    start = unit.text.find(quote)
    return RagCitation(
        citation_id=f"CIT-{answer_id[-12:]}-{unit.evidence_id[-6:]}",
        citation_label=unit.citation_label,
        evidence_id=unit.evidence_id,
        retrieval_unit_id=unit.retrieval_unit_id,
        document_id=unit.document_id,
        section_id=unit.section_id,
        sentence_id=unit.sentence_id,
        claim_ids=[claim_id],
        quoted_span=quote,
        quoted_span_start=max(0, start),
        quoted_span_end=max(0, start) + len(quote),
        source_text_checksum=unit.text_checksum,
        citation_status="valid",
    )
