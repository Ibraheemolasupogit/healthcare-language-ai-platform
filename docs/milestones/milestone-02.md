# Milestone 2

## Objective

Create deterministic synthetic clinical-document generation and validated
document fixtures for future NLP and evaluation milestones.

## Scope

Milestone 2 adds controlled vocabularies, templates, deterministic identifiers,
generation commands, annotations, manifests, quality reports, schemas, tests,
fixture reproducibility, and documentation.

## Files Introduced

The milestone introduces `src/healthcare_language_ai/synthetic`, JSON schemas
under `schemas/synthetic`, fixture evidence under `tests/fixtures/synthetic`,
and synthetic-data design, schema, and validation documentation.

## Generation Design

Generation uses local seeded RNGs, fixed reference timestamps, versioned
templates, small controlled vocabularies, and stable JSON serialization.

## Determinism Controls

The same count, seed, document types, reference timestamp, generator version,
template version, and vocabulary version produce byte-for-byte identical
canonical files.

## Governance Controls

All generated records are classified synthetic, use synthetic identifiers, avoid
real-person fields, and are checked for suspicious privacy patterns and
prohibited recommendation wording.

## Validation Performed

Validation covers data quality, annotation offsets, manifest counts, checksums,
fixture reproducibility, schema validation, CLI behavior, linting, type checks,
and tests.

## Explicit Exclusions

No real patient data, downloaded datasets, NLP models, embeddings, semantic
search, RAG, APIs, Streamlit, Snowflake, Databricks, Fabric, cloud resources,
commits, pushes, or pull requests.

## Definition of Done

The milestone is done when fixtures regenerate exactly, validation passes, tests
pass above coverage threshold, and documentation clearly states safety limits.

## Next Milestone

Milestone 3 should add local ingestion and Snowflake-oriented contracts without
creating live cloud connections.
