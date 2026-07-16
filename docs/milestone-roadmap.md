# Milestone Roadmap

Milestone 12 closes the local portfolio build with final repository audit,
architecture evidence, traceability, reviewer guides, evidence index, model
card, release-readiness gates, release manifest and local release package.

Later milestone scope may be refined based on implementation evidence.

1. Milestone 1: Repository foundation.
2. Milestone 2: Deterministic synthetic clinical text and validated fixtures.
3. Milestone 3: Local ingestion and Snowflake-oriented contracts.
4. Milestone 4: Local preprocessing and Databricks-style pipeline contracts.
5. Milestone 5: Clinical entity extraction and classification.
6. Milestone 6: Embeddings and semantic retrieval.
7. Milestone 7: Retrieval quality improvement and benchmark selection.
8. Milestone 8: Retrieval remediation, paraphrase robustness, and adjudication.
9. Milestone 9: Guarded synthetic RAG orchestration and evaluation.
10. Milestone 10: Inference API, demo interface, or portfolio experience.
11. Milestone 11: Local platform hardening, contract evolution, runtime
    resilience, and operational assurance.
12. Milestone 12: Future scope; not implemented here.
## Milestone 5 Status

Milestone 5 is implemented as a deterministic rule-based baseline for synthetic
entity extraction, document classification, evaluation, error analysis, model-card
evidence, and MLflow dry-run planning. Later milestones are intentionally not
implemented here.

## Milestone 6 Status

Milestone 6 is implemented as a local retrieval benchmark with keyword, TF-IDF,
BM25, deterministic hash-vector, and hybrid retrieval. Later RAG or production
search milestones are intentionally not implemented.
## Milestone 7

Milestone 7 implements local retrieval-quality improvement and independent benchmarking. It selects a model-free baseline candidate but reports `not_approved` for future RAG prototype work because required quality gates do not yet pass. Milestone 8 should not begin until those retrieval gates are remediated or consciously re-scoped.

## Milestone 8

Milestone 8 implements retrieval failure analysis, benchmark v2.1 adjudication,
character/phrase/proximity/synonym/pseudo-feedback remediation, ensemble
reranking, diversification, confidence scoring, abstention, and comparison
approval. It approves `abstaining_ensemble_v1` only for future synthetic RAG
prototype planning. It does not implement RAG, answer generation, prompt
orchestration, hosted embeddings, live vector search, API, Streamlit, or
clinical deployment.

## Milestone 9

Milestone 9 implements guarded synthetic RAG orchestration, deterministic
generation, citation validation, groundedness checks, refusal/safety controls,
evaluation gates, and local-demo approval. It does not implement hosted LLMs,
production APIs, UI, cloud deployment, or clinical validation.

## Milestone 10

Milestone 10 implements local read-only application services, FastAPI, Streamlit,
operational observability, deterministic demo sessions, and portfolio evidence
summaries over approved synthetic RAG fixtures. It does not implement production
authentication, hosted models, cloud deployment, or real healthcare
integrations.

## Milestone 11

Milestone 11 implements local contract compatibility assurance, configuration
hardening, lifespan/readiness checks, local rate limiting, bounded runtime smoke
tests, operational event integrity, deterministic backup/recovery, static
security scans, dependency inventory, SBOM evidence, static container assurance,
and portfolio assurance gates. It does not implement target-state cloud
deployment, production auth, hosted models, real integrations, or Milestone 12.
