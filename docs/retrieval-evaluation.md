# Retrieval Evaluation

Retrieval evaluation calculates Precision@k, Recall@k, Hit Rate@k, MRR, MAP,
NDCG@k, zero-hit queries, failures, and average relevant rank for k values 1, 3,
5, and 10.

Metrics are grouped by query category and leakage risk. Relevance grades are
`0 = not relevant`, `1 = relevant`, and `2 = highly relevant`.
## Configuration Comparison

Milestone 7 evaluates registered model-free retrieval configurations on development and validation splits, selects by validation NDCG@5, and calculates holdout metrics after selection. Quality gates derive the final approval status.

