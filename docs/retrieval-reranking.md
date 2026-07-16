# Retrieval Reranking

The reranking layer is local and transparent. The checked-in baselines include no reranker, a metadata-aware reranker, and a feature-weighted reranker.

Features include lexical score, deterministic hash-vector score, metadata compatibility, negation compatibility, numeric compatibility, unit compatibility, granularity preference, and deterministic tie-breaking.

No cross-encoder is required for default validation.
