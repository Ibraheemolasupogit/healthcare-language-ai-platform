"""Controlled local vocabularies for deterministic synthetic generation."""

from __future__ import annotations

VOCABULARY_VERSION = "1.0.0"

PRESENTING_CONCERNS = [
    "simulated chest tightness",
    "synthetic abdominal discomfort",
    "fictional shortness of breath episode",
    "simulated headache review",
    "synthetic joint swelling",
]

OBSERVATIONS = [
    "temperature 36.8 C, pulse 78, blood pressure 128 over 76",
    "temperature 37.1 C, pulse 84, blood pressure 134 over 82",
    "oxygen saturation 98 percent on air, pulse 72",
    "respiratory rate 16, oxygen saturation 97 percent on air",
]

BODY_SITES = ["chest", "abdomen", "left knee", "head", "right wrist"]
INVESTIGATIONS = [
    "synthetic full blood count",
    "simulated chest radiograph",
    "fictional ultrasound abdomen",
    "synthetic knee radiograph",
    "simulated pathology panel",
]
ENCOUNTER_CONTEXTS = [
    "synthetic outpatient attendance",
    "simulated same-day assessment",
    "fictional observation unit encounter",
]
WORKFLOW_STATUSES = ["draft", "quality_checked", "ready_for_nlp_fixture"]
SPECIALTIES = ["general medicine", "respiratory", "gastroenterology", "radiology", "pathology"]
ADMINISTRATIVE_PRIORITIES = ["routine_simulation", "standard_review", "workflow_queue_a"]
REPORT_DESCRIPTORS = [
    "mild simulated change",
    "no focal simulated abnormality",
    "stable fictional finding",
]
FOLLOW_UP_PLACEHOLDERS = [
    "Follow-up placeholder for synthetic workflow tracking only.",
    "Administrative review placeholder; not clinical guidance.",
    "Simulation follow-up field retained for downstream testing.",
]
