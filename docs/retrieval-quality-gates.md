# Retrieval Quality Gates

Quality gates define whether a retrieval configuration may be approved for future RAG prototype work. Required gates include validation Hit Rate@5, Recall@5, NDCG@5, paraphrased Hit Rate@5, negation-sensitive Hit Rate@5, holdout Hit Rate@5, holdout NDCG@5, and zero-hit limits.

Gates are not weakened to force approval. The current checked-in decision is `not_approved`.

Milestone 9 adds separate RAG quality gates for citation validity, refusal
accuracy, unsupported-claim rate, safety violations, and holdout grounded-answer
rate. Passing RAG gates does not imply clinical approval.
