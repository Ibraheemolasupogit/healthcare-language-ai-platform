# Retrieval Configuration Comparison

Milestone 7 uses a finite versioned configuration registry. Model-free configurations are evaluated by default; optional local dense configurations are skipped explicitly when no local model is supplied.

Selection uses development and validation evidence only, with validation NDCG@5 as the primary metric. Holdout metrics are calculated after selection and reported separately.
