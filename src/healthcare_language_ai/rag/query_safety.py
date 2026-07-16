"""Deterministic query safety classification."""

from __future__ import annotations

from healthcare_language_ai.rag.contracts import QuerySafetyClassification

UNSUPPORTED_RULES = [
    ("unsupported_emergency_request", ["emergency", "urgent care", "911", "life threatening"]),
    ("unsupported_real_patient_request", ["my patient", "real patient", "actual patient"]),
    ("unsupported_medication_request", ["medication", "prescribe", "dosage", "take aspirin"]),
    ("unsupported_treatment_request", ["treatment", "therapy", "what should", "should i"]),
    ("unsupported_diagnosis_request", ["diagnose", "diagnosis", "do i have"]),
    ("unsupported_clinical_advice", ["clinical advice", "medical advice", "recommend"]),
]


def classify_query(
    query_id: str, query_text: str, *, portfolio_demo: bool = True
) -> QuerySafetyClassification:
    lowered = query_text.lower()
    for category, patterns in UNSUPPORTED_RULES:
        if any(pattern in lowered for pattern in patterns):
            return QuerySafetyClassification(
                query_id=query_id,
                category=category,
                allowed_for_retrieval=False,
                refusal_reason=category,
            )
    if "synthetic" in lowered or portfolio_demo:
        category = (
            "synthetic_summary_request" if "summary" in lowered else "synthetic_record_lookup"
        )
        if "compare" in lowered:
            category = "synthetic_comparison"
        if "metadata" in lowered:
            category = "synthetic_metadata_query"
        return QuerySafetyClassification(
            query_id=query_id,
            category=category,
            allowed_for_retrieval=True,
        )
    return QuerySafetyClassification(
        query_id=query_id,
        category="out_of_scope",
        allowed_for_retrieval=False,
        refusal_reason="out_of_scope",
    )
