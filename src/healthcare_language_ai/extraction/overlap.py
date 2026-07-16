"""Auditable deterministic overlap resolution."""

from __future__ import annotations

from healthcare_language_ai.extraction.contracts import RuleMatch, SuppressedCandidate

OVERLAP_RESOLUTION_VERSION = "1.0.0"


def _overlaps(left: RuleMatch, right: RuleMatch) -> bool:
    return left.document_id == right.document_id and max(
        left.start_offset, right.start_offset
    ) < min(left.end_offset, right.end_offset)


def _ranking_key(candidate: RuleMatch) -> tuple[int, int, int, int, int, str]:
    span_length = candidate.end_offset - candidate.start_offset
    return (
        -candidate.priority,
        -span_length,
        candidate.start_offset,
        candidate.end_offset,
        0 if candidate.section_label else 1,
        candidate.rule_id,
    )


def resolve_overlaps(
    candidates: list[RuleMatch],
) -> tuple[list[RuleMatch], list[SuppressedCandidate], int]:
    accepted: list[RuleMatch] = []
    suppressed: list[SuppressedCandidate] = []
    seen_prediction_keys: set[tuple[str, str, int, int, str]] = set()
    duplicate_count = 0
    for candidate in sorted(candidates, key=_ranking_key):
        key = (
            candidate.document_id,
            candidate.label,
            candidate.start_offset,
            candidate.end_offset,
            candidate.normalised_value,
        )
        if key in seen_prediction_keys:
            duplicate_count += 1
            continue
        overlap_winner = next((item for item in accepted if _overlaps(candidate, item)), None)
        if overlap_winner is not None:
            suppressed.append(
                SuppressedCandidate(
                    candidate_id=candidate.candidate_id,
                    document_id=candidate.document_id,
                    label=candidate.label,
                    start_offset=candidate.start_offset,
                    end_offset=candidate.end_offset,
                    rule_id=candidate.rule_id,
                    suppressed_by_candidate_id=overlap_winner.candidate_id,
                    suppression_reason="overlap_resolution_priority_length_position_rule",
                    extraction_run_id=candidate.extraction_run_id,
                )
            )
            continue
        accepted.append(candidate)
        seen_prediction_keys.add(key)
    accepted.sort(
        key=lambda item: (item.document_id, item.start_offset, item.end_offset, item.label)
    )
    suppressed.sort(key=lambda item: (item.document_id, item.start_offset, item.rule_id))
    return accepted, suppressed, duplicate_count
