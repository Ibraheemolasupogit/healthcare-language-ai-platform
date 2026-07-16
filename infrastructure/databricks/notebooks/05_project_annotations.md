# 05 Project Annotations

Purpose: project source annotation offsets into normalised text where safe.

Inputs: canonical annotations and processed documents.
Outputs: silver projected annotations.
Parameters: projection rules version.
Validation gates: exact target-span matching.
Failure behaviour: unresolved projections are retained, never guessed.
Observability: projection-status counts.
Security: no inferred clinical entities.
Local mapping: `preprocessing.offsets`.
