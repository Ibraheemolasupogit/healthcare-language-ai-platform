"""Versioned prompt-contract assets for synthetic RAG."""

from __future__ import annotations

from pathlib import Path

import yaml

from healthcare_language_ai.rag.contracts import PromptContract

PROMPT_VERSION = "1.0.0"
PROMPT_IDS = [
    ("grounded-answer", "grounded_answer"),
    ("multi-evidence-answer", "multi_evidence_answer"),
    ("conflicting-evidence", "conflicting_evidence"),
    ("insufficient-evidence-refusal", "insufficient_evidence_refusal"),
    ("unsupported-clinical-request", "unsupported_clinical_request"),
    ("citation-repair", "citation_repair"),
]


def default_prompt_contract(prompt_id: str, purpose: str) -> PromptContract:
    return PromptContract(
        prompt_id=prompt_id,
        prompt_version=PROMPT_VERSION,
        purpose=purpose,
        allowed_input_fields=[
            "query",
            "retrieval_status",
            "evidence_units",
            "safety_classification",
        ],
        required_output_fields=["answer_status", "answer_text", "claims", "citations"],
        citation_format="[E<number>]",
        refusal_rules=["refuse unsupported clinical requests", "refuse retrieval abstention"],
        prohibited_content=[
            "diagnosis",
            "treatment advice",
            "medication advice",
            "patient-specific medical advice",
        ],
        maximum_context_size=6000,
        maximum_answer_size=900,
        safety_disclaimer="Synthetic portfolio prototype only; not for clinical use.",
    )


def write_default_prompt_assets(root: Path = Path("models/prompts/rag")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for prompt_id, purpose in PROMPT_IDS:
        contract = default_prompt_contract(prompt_id, purpose)
        (root / f"{prompt_id}.yaml").write_text(
            yaml.safe_dump(contract.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )
    readme = (
        "# RAG Prompt Contracts\n\n"
        "Local prompt contracts only; no provider credentials or live prompts.\n"
    )
    (root / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    return root


def load_prompt_contract(prompt_id: str, root: Path = Path("models/prompts/rag")) -> PromptContract:
    path = root / f"{prompt_id}.yaml"
    if not path.exists():
        write_default_prompt_assets(root)
    return PromptContract.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
