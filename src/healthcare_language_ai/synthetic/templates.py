"""Versioned synthetic document templates."""

from __future__ import annotations

from dataclasses import dataclass

from healthcare_language_ai.domain.enums import ClinicalDocumentType

TEMPLATE_VERSION = "1.0.0"


@dataclass(frozen=True)
class TemplateResult:
    template_name: str
    text: str
    span_values: dict[str, str]
    document_level: dict[str, str]


def render_template(document_type: ClinicalDocumentType, values: dict[str, str]) -> TemplateResult:
    """Render a versioned synthetic template for a document type."""
    common = "This is a synthetic document for educational NLP testing only."
    if document_type is ClinicalDocumentType.CLINICAL_NOTE:
        text = "\n".join(
            [
                common,
                f"Reason for attendance: {values['presenting_concern']}.",
                f"Relevant history: Fictional history linked to {values['encounter_context']}.",
                f"Observations: {values['observation']}.",
                f"Assessment summary: Simulation summary for {values['body_site']} review.",
                (
                    "Plan recorded for simulation: Placeholder workflow note only; "
                    "not clinical guidance."
                ),
            ]
        )
        labels = ["presenting_concern", "encounter_context", "observation", "body_site"]
    elif document_type is ClinicalDocumentType.DISCHARGE_SUMMARY:
        text = "\n".join(
            [
                common,
                f"Admission reason: {values['presenting_concern']}.",
                f"Synthetic hospital-course summary: Monitored in {values['encounter_context']}.",
                f"Recorded investigations: {values['investigation']}.",
                f"Discharge status: {values['workflow_status']}.",
                f"Follow-up placeholder: {values['follow_up']}",
            ]
        )
        labels = ["presenting_concern", "encounter_context", "investigation", "workflow_status"]
    elif document_type is ClinicalDocumentType.REFERRAL_LETTER:
        text = "\n".join(
            [
                common,
                f"Referral reason: {values['presenting_concern']}.",
                f"Relevant synthetic history: {values['encounter_context']} in portfolio fixture.",
                f"Current concerns: Review of {values['body_site']} with {values['descriptor']}.",
                f"Requested review: {values['specialty']} review for simulation workflow.",
                f"Administrative priority label: {values['administrative_priority']}.",
            ]
        )
        labels = [
            "presenting_concern",
            "encounter_context",
            "body_site",
            "descriptor",
            "specialty",
            "administrative_priority",
        ]
    elif document_type is ClinicalDocumentType.RADIOLOGY_REPORT:
        text = "\n".join(
            [
                common,
                f"Study: {values['investigation']}.",
                f"Synthetic indication: {values['presenting_concern']}.",
                f"Findings: {values['descriptor']} involving {values['body_site']}.",
                "Impression: Synthetic radiology-style report for fixture validation only.",
            ]
        )
        labels = ["investigation", "presenting_concern", "descriptor", "body_site"]
    else:
        text = "\n".join(
            [
                common,
                f"Specimen type: synthetic specimen from {values['body_site']}.",
                f"Macroscopic description: {values['descriptor']} in fictional specimen container.",
                f"Microscopic description: Simulated cellular notes for {values['specialty']}.",
                f"Synthetic interpretation label: {values['workflow_status']}.",
            ]
        )
        labels = ["body_site", "descriptor", "specialty", "workflow_status"]

    span_values = {label: values[label] for label in labels}
    return TemplateResult(
        template_name=document_type.value,
        text=f"{text}\n",
        span_values=span_values,
        document_level={
            "synthetic_subject_id": values["synthetic_subject_id"],
            "synthetic_encounter_id": values["synthetic_encounter_id"],
            "document_type": document_type.value,
            "seed": values["seed"],
            "record_index": values["record_index"],
        },
    )
