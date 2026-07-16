# Milestone 4

## Objective

Implement deterministic local clinical-text preprocessing and Databricks-style
pipeline contracts without Databricks connectivity or PySpark.

## Scope

Milestone 4 adds text normalisation, section parsing, sentence segmentation,
lexical-token statistics, annotation projection, quality evidence,
preprocessing manifests, reconciliation, Databricks dry-run plans, schemas,
fixtures, tests, and documentation.

## Explicit Exclusions

No Databricks connection, PySpark, Spark, workspace, clusters, Delta deployment,
NER models, classification models, clinical coding, embeddings, RAG, LLMs, API,
UI, Fabric, Power BI, commits, pushes, or pull requests.

## Definition Of Done

The milestone is done when preprocessing fixtures reproduce exactly, source text
preservation and offsets validate, Databricks planning confirms no connection,
and all local quality gates pass.

## Next Milestone

Milestone 5 should add clinical entity extraction contracts using the existing
synthetic annotations, without trained models unless explicitly scoped.
