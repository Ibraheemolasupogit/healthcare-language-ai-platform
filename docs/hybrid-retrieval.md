# Hybrid Retrieval

Hybrid retrieval uses weighted normalised score fusion across keyword, TF-IDF,
BM25, deterministic hash-vector similarity, and metadata score. Weights are
configured, non-negative, and require at least one positive value.

Metadata filters are applied before ranking using explicit supported fields only.
## Feature-Reranked Hybrid

Milestone 7 adds a model-free feature-reranked hybrid configuration using deterministic hash vectors, lexical evidence, metadata compatibility, negation compatibility, numeric compatibility, and granularity preference. It is selected by validation NDCG@5 but is not approved by required gates.

