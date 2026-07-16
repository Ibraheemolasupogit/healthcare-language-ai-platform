# Milestone 3

## Objective

Implement local deterministic ingestion for synthetic datasets and
Snowflake-oriented data contracts without live Snowflake connectivity.

## Scope

Milestone 3 adds source discovery, manifest validation, canonical document and
annotation rows, deterministic CSV and Parquet outputs, ingestion manifests,
reconciliation reports, quarantine-ready evidence, Snowflake dry-run load plans,
SQL reference assets, schemas, tests, fixtures, and documentation.

## Ingestion Design

The pipeline validates source files and source quality, loads documents and
annotations, normalises to canonical rows while preserving text and offsets,
writes local evidence, and validates a target-state Snowflake plan.

## Canonical Contracts

Contracts include canonical clinical documents, canonical annotations,
quarantine records, reconciliation metrics, ingestion manifests, Snowflake table
contracts, and load plans.

## Reconciliation

Reconciliation derives overall status from count, checksum, duplicate,
referential-integrity, distribution, governance, and Snowflake-plan checks.

## Quarantine Behaviour

Strict mode fails on invalid source records. Quarantine mode records rejected
items with sanitized metadata and deterministic timestamps without silently
dismissing records.

## Snowflake Reference Architecture

Snowflake assets are table contracts, local file-format assumptions, dry-run load
plans, and reference SQL only. No SQL is executed.

## Explicit Exclusions

No Snowflake connector, SnowSQL, live account access, credentials, cloud stages,
deployed databases, Terraform, Databricks, Spark, NLP, embeddings, RAG, APIs,
dashboards, commits, pushes, or pull requests.

## Definition of Done

The milestone is done when ingestion fixtures reproduce deterministically,
schemas validate evidence, local validation passes, and Snowflake planning
confirms no external connection.

## Next Milestone

Milestone 4 should add local preprocessing and Databricks-style NLP pipeline
contracts without Spark or Databricks runtime dependencies unless explicitly
scoped.
