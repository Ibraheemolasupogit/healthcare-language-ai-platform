# Milestone 8: Retrieval Remediation

Milestone 8 remediates the Milestone 7 retrieval-quality failure profile without
adding RAG, prompt orchestration, answer generation, hosted embeddings, live
Databricks Vector Search, or clinical deployment.

Implemented evidence:

- Failure inventory for the Milestone 7 selected baseline.
- Synthetic judgment audit and non-mutating benchmark v2.1 upgrade.
- Character n-gram, phrase, proximity, synonym, pseudo-feedback, field-aware,
  entity-aware, reranking, diversification, confidence, and abstention features.
- Ten model-free remediation configurations.
- Validation-selected comparison with holdout metrics computed after selection.
- MLflow, Databricks, and Vector Search dry-run contracts.

Approval boundary:

`abstaining_ensemble_v1` is approved only for future synthetic RAG prototype
planning. The evidence is synthetic, not clinician reviewed, and does not claim
clinical-search performance.
