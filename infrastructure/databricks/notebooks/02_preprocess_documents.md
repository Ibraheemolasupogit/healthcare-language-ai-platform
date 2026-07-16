# 02 Preprocess Documents

Purpose: create preserved and normalised document representations.

Inputs: canonical clinical documents.
Outputs: silver processed document rows.
Parameters: preprocessing mode, normalisation version.
Validation gates: source text preservation and deterministic checksums.
Failure behaviour: stop on mandatory failures.
Observability: document counts and quality counts only.
Security: no clinical text in logs.
Local mapping: `preprocessing.normalisation` and `preprocessing.pipeline`.
