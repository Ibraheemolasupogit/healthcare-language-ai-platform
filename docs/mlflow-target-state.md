# MLflow Target State

MLflow is represented as a dry-run contract only. The plan records experiment
placeholder, run name, parameters, metrics, tags, artifacts, dataset lineage, rule
versions, model-card artifacts, and registry-stage placeholder.

No tracking URI, workspace URL, token, secret, registry credential, or connection
option is included.

Milestone 6 extends the dry-run plan with retrieval index IDs, retrieval run IDs,
retrieval evaluation IDs, query-set lineage, retrieval metrics, model/index card
artifacts, and failure-analysis artifacts.
## Retrieval Quality Comparison Plan

Milestone 7 writes an MLflow comparison dry-run plan for retrieval-quality experiments. It records intended experiment metadata without contacting an MLflow Tracking Server.

## RAG Dry-Run Plan

Milestone 9 writes an MLflow RAG dry-run plan with RAG run ID, evaluation ID,
prompt versions, generator parameters, metrics and artifacts. It records
`connection_attempted: false` and `execution_permitted: false`.
