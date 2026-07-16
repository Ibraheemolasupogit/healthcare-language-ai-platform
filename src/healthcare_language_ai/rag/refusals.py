"""Deterministic refusal templates for guarded synthetic RAG."""

from __future__ import annotations

REFUSAL_TEMPLATE_VERSION = "1.0.0"

REFUSALS = {
    "unsupported_clinical_advice": (
        "This synthetic portfolio system cannot provide clinical advice or "
        "patient-specific conclusions."
    ),
    "unsupported_diagnosis_request": (
        "This synthetic portfolio system cannot provide diagnosis or diagnostic certainty."
    ),
    "unsupported_treatment_request": (
        "This synthetic portfolio system cannot provide treatment recommendations."
    ),
    "unsupported_medication_request": (
        "This synthetic portfolio system cannot provide medicine-specific guidance."
    ),
    "unsupported_real_patient_request": (
        "This synthetic portfolio system cannot process real-patient requests."
    ),
    "unsupported_emergency_request": (
        "This synthetic portfolio system cannot provide emergency guidance."
    ),
    "retrieval_abstention": (
        "The approved synthetic retriever abstained, so no grounded response is generated."
    ),
    "unanswerable_query": (
        "The available synthetic evidence is insufficient for a grounded response."
    ),
    "metadata_filter_empty": (
        "The metadata-filtered synthetic evidence set is empty, so no grounded "
        "response is generated."
    ),
    "citation_validation_failed": (
        "Citation validation failed, so the generated response is not promoted."
    ),
    "groundedness_validation_failed": (
        "Groundedness validation failed, so the generated response is not promoted."
    ),
    "safety_validation_failed": (
        "Safety validation failed, so the generated response is not promoted."
    ),
}


def refusal_text(reason: str) -> str:
    return REFUSALS.get(reason, REFUSALS["unanswerable_query"])
