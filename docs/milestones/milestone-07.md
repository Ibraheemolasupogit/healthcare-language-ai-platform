# Milestone 7: Retrieval Quality Improvement

Milestone 7 adds independent synthetic holdout evidence, an expanded retrieval benchmark, deterministic query expansion, negation and numeric features, cross-granularity retrieval policies, reranking baselines, configuration comparison, quality gates, and an approval decision for future RAG prototype planning.

The selected model-free baseline is derived from validation metrics only. Holdout metrics are written after selection. The current checked-in comparison selects `feature_reranked_hybrid_v1`, but the approval decision is `not_approved` because required quality gates do not pass.

This milestone does not implement RAG, answer generation, hosted embeddings, cloud connections, or clinician-validated relevance judgments.
