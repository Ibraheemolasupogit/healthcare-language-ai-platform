# Data Governance

Milestone 12 preserves the synthetic-only governance boundary in the final
portfolio package. Release readiness explicitly records that the repository is
not clinically validated, not production ready, not cloud deployed, and not
connected to real patient systems.

## Synthetic-Data-Only Policy

This repository is built for synthetic data only. Real patient records must not
be added, downloaded, copied, transformed, tested, or referenced.

## Prohibited Use

The platform is not a medical device, is not intended for clinical use, and must
not provide diagnosis, treatment recommendations, medication recommendations,
patient-specific advice, or automated clinical decision-making.

## Data Minimisation

Domain models avoid direct identifiers. Safe synthetic concepts such as
`synthetic_subject_id` and `synthetic_encounter_id` may be used for reproducible
testing.

## Safe Logging

Logs must not contain full clinical text, secrets, credentials, tokens, or
sensitive document content. Logging helpers redact common sensitive fields and
support correlation IDs.

Milestone 2 validation also checks generated text for suspicious patterns such
as NHS-number-like values, email addresses, UK telephone numbers, postcodes,
URLs, IPv4 addresses, credit-card-like values, National Insurance-like values,
and unapproved long numeric identifiers. These are portfolio safeguards, not a
replacement for production de-identification or disclosure-control systems.

Templates are checked for prohibited recommendation-style phrases including
`you should take`, `start taking`, `stop taking`, `recommended treatment`,
`medical advice`, `diagnosis confirmed`, and `urgent treatment required`.

Milestone 3 ingestion preserves synthetic lineage, verifies source manifests and
checksums, and writes local evidence only. Snowflake assets are reference-only
and do not create accounts, roles, schemas, tables, stages, or credentials.

Milestone 4 preprocessing preserves source text, records derived text fields,
and performs no diagnosis, treatment inference, clinical coding, NER, embedding,
LLM, PySpark, or Databricks execution. Databricks assets are target-state
contracts only.

## Safe Output Handling

Local data, output, and report folders are ignored by Git by default. Generated
artifacts should remain synthetic and reproducible.

## Retention Assumptions

Milestone 1 does not implement retention automation. Later milestones should
define retention windows for synthetic intermediate and derived outputs.

## Future Governance Controls

Later milestones may add schema contracts, lineage manifests, quality checks,
human review workflows, and policy checks before publishing artifacts.

## Human Review Expectations

All demonstrations should clearly state that outputs are synthetic and
educational. Human reviewers should verify no real clinical data has entered the
repository.
## Milestone 5 Governance

Extraction and evaluation remain synthetic-data-only. Rules use local controlled
vocabularies, summaries avoid full clinical text, and MLflow/Databricks artifacts
are dry-run target-state contracts with no credentials or connections.

## Milestone 6 Governance

Retrieval indexes and query fixtures remain synthetic only. Snippets are bounded,
full documents are not printed in summaries, and all vector-search and MLflow
artifacts are dry-run contracts with no credentials.
## Retrieval Quality Governance

Milestone 7 holdout and benchmark evidence remains synthetic-only. The reviewer pack is human-review-ready but does not claim clinician validation. Optional local embedding models must be supplied from explicit local paths and are never downloaded by default validation.

## Milestone 9 RAG Governance

RAG evidence remains synthetic-only. RAG expected outcomes are not clinician
reviewed, deterministic answers are fixed-template outputs, and groundedness
means repository-evidence traceability rather than clinical truth.
