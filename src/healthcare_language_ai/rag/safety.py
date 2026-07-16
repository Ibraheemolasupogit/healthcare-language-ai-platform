"""Generated-answer safety validation."""

from __future__ import annotations

from healthcare_language_ai.rag.contracts import SafetyValidationResult

PROHIBITED_PATTERNS = [
    "you should take",
    "start taking",
    "stop taking",
    "recommended treatment",
    "diagnosis confirmed",
    "urgent treatment required",
    "seek emergency care",
    "medical advice",
    "prescribe",
    "dosage",
]


def validate_safety(answer_id: str, query_id: str, answer_text: str) -> SafetyValidationResult:
    lowered = answer_text.lower()
    matches = [pattern for pattern in PROHIBITED_PATTERNS if pattern in lowered]
    return SafetyValidationResult(
        answer_id=answer_id,
        query_id=query_id,
        safety_status="failed" if matches else "passed",
        violation_count=len(matches),
        prohibited_patterns=matches,
    )
