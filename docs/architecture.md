# Architecture

Milestone 12 adds a final portfolio packaging layer around the local synthetic
platform. The layer does not introduce production services; it generates
repository audit evidence, architecture artifacts, traceability, run registry,
release-readiness reports, and a local reviewer package from existing checked
fixtures and reports.

## Architectural Goals

The platform is designed to be modular, testable, reproducible, and safe for
portfolio demonstration. Milestone 1 establishes contracts and boundaries before
adding data processing behavior.

## Logical Components

- `config`: typed settings and validation.
- `domain`: synthetic clinical text contracts and pipeline run metadata.
- `logging`: structured, content-safe observability helpers.
- `utils`: deterministic identifiers and timezone-aware time helpers.
- `synthetic`: deterministic template-based document generation, annotations,
  manifests, validation, and quality reports.
- `ingestion`: local source discovery, manifest-driven validation, canonical
  row modelling, reconciliation, deterministic exports, and Snowflake dry-run
  planning.
- `preprocessing`: local text normalisation, section parsing, sentence
  segmentation, lexical-token statistics, annotation projection, quality
  reporting, and Databricks dry-run planning.
- Future modules: ingestion, preprocessing, extraction, embeddings, retrieval,
  inference, evaluation, monitoring, and reporting.

```mermaid
flowchart TD
    CLI[Typer CLI] --> Config[Typed configuration]
    CLI --> Domain[Domain contracts]
    Config --> Logging[Structured logging]
    Domain --> Future[Future pipeline modules]
    Future -. target state .-> Snowflake[(Snowflake)]
    Future -. target state .-> Databricks[(Databricks)]
    Future -. target state .-> MLflow[(MLflow)]
    Future -. target state .-> Fabric[Fabric and Power BI]
```

## Module Boundaries

Milestone 1 modules must be import-safe and must not mutate the filesystem at
import time. CLI commands are the boundary for validation and local directory
creation.

## Data Flow

The target-state flow starts with synthetic clinical text, then moves through
ingestion, preprocessing, extraction and classification, embeddings, retrieval
and RAG, evaluation and monitoring, and finally APIs, apps, and reporting.

## Configuration Model

Configuration precedence is: code defaults, YAML file values, then environment
variables and optional `.env` values. Paths are represented with `pathlib.Path`.
Invalid YAML, missing YAML, and structurally invalid configuration raise custom
configuration errors.

## Domain Contracts

Domain models represent document type, status, classification, clinical
documents, processing records, and pipeline runs. Clinical documents default to
synthetic classification and reject non-synthetic document instances in this
milestone.

Milestone 2 adds persisted synthetic evidence contracts for generated documents,
document annotations, dataset manifests, and data-quality reports. The manifest
checksums the canonical JSONL document and annotation files, avoiding circular
manifest hashing.

Milestone 3 adds canonical row contracts for local ingestion. Canonical CSV and
JSON evidence are deterministic. Parquet is included for target-state analytics
compatibility and is verified for logical equivalence.

## Observability Model

Logging uses `structlog` with console output for local development and JSON for
future automated environments. Correlation fields include run ID, document ID,
and pipeline stage. Full clinical text and secrets are redacted.

## Future Platform Roles

Snowflake will eventually hold governed analytical data products and contracts.
Databricks will eventually support scalable preprocessing and NLP experiments.
MLflow will eventually track model and evaluation evidence. Fabric and Power BI
will eventually provide executive reporting surfaces.

## Deployment Boundaries

Milestone 1 includes only a local Docker baseline and CI quality gates. It does
not include Terraform, Bicep, cloud deployments, or credentials.

## Security and Privacy Constraints

The project prohibits real patient data, direct identifiers, clinical advice,
and automated clinical decision-making. Outputs and logs must be treated as safe
synthetic artifacts.

## Design Trade-offs

The foundation favors explicit contracts and simple modules over abstract
interfaces. This keeps the first milestone understandable while leaving room for
later platform integrations.
## Milestone 5 Baseline NLP Layer

Milestone 5 adds a local, deterministic rule-based NLP layer after preprocessing.
It loads controlled vocabularies, generates exact span predictions, classifies
document type from section headings, evaluates predictions against projected
synthetic annotations, and writes model-card and MLflow dry-run evidence.

The layer is a transparent portfolio baseline, not a clinically validated NLP
system.

## Milestone 6 Retrieval Layer

Milestone 6 adds local retrieval units, sparse retrieval, deterministic hash
vectors, hybrid ranking, metadata filters, query fixtures, retrieval metrics,
failure analysis, and dry-run MLflow/Vector Search plans. It returns evidence
passages only and does not generate answers.
## Milestone 7 Retrieval Quality Layer

The retrieval quality layer adds an independent synthetic holdout corpus, an expanded benchmark, query expansion, negation and numeric features, cross-granularity retrieval policies, feature reranking, deterministic configuration comparison, and quality-gate-derived approval decisions. It remains local, model-free by default, and does not generate answers.

## Milestone 9 Guarded RAG Layer

Milestone 9 validates the approved retrieval baseline, assembles bounded
evidence, applies versioned prompt contracts, uses deterministic generation,
validates citations and groundedness, and evaluates refusal/safety behaviour.
It is not a production API or clinical system.
