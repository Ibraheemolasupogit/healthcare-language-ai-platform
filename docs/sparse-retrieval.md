# Sparse Retrieval

The local sparse baselines are keyword coverage, TF-IDF cosine similarity, and
BM25 Okapi. Tokenisation is versioned and preserves negation, numbers, units, and
synthetic identifiers. BM25 records `k1`, `b`, corpus size, average length, and
document frequencies.

Scores are normalised per query. Ties are broken deterministically by unit type,
document ID, and retrieval-unit ID.

