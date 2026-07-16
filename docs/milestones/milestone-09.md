# Milestone 9: Guarded Synthetic RAG Orchestration

Milestone 9 adds a local, model-free, guarded synthetic RAG prototype on top of
the approved Milestone 8 `abstaining_ensemble_v1` retriever.

Implemented:

- Retrieval approval validation before RAG execution.
- Deterministic query safety classification.
- Retrieval-abstention propagation.
- Bounded evidence assembly and citation labels.
- Versioned prompt contracts under `models/prompts/rag`.
- Deterministic citation-bearing answer generation.
- Citation, groundedness, conflict, refusal and safety validation.
- RAG evaluation metrics, quality gates, model card, approval decision, and
  MLflow/Databricks dry-run plans.

Not implemented: hosted LLMs, automatic model downloads, production API, user
interface, cloud deployment, clinical validation, diagnosis, treatment advice,
medication advice, or patient-specific guidance.
