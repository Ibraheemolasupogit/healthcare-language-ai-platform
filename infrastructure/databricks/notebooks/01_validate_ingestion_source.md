# 01 Validate Ingestion Source

Purpose: validate local ingestion evidence before preprocessing.

Inputs: ingestion manifest, canonical documents, canonical annotations.
Outputs: validation status for downstream preprocessing.
Parameters: ingestion directory, reference timestamp, contract versions.
Validation gates: checksums, governance flags, row counts, schema contracts.
Failure behaviour: stop the target-state job.
Observability: emit run ID and validation metrics only.
Security: synthetic data only, no secrets.
Local mapping: `preprocess-run` source validation.
