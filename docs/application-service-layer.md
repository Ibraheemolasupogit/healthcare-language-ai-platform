# Application Service Layer

The application package provides shared read-only services for query execution, answer lookup, evidence browsing, trace inspection, approval summaries, readiness, and metrics.

The CLI, FastAPI app, Streamlit dashboard, tests, demo runner, and portfolio summary all use `build_services()`. The service layer indexes approved fixture-backed RAG outputs and returns bounded contracts. It does not mutate canonical fixtures or duplicate RAG business logic in UI routes.

Errors are normalized at the API boundary. Lineage is preserved through answer IDs, query IDs, evidence IDs, citation IDs, retrieval approval IDs, prompt IDs, generator metadata, and quality validation statuses.
