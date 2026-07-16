# 06 Quality And Reconciliation

Purpose: compute quality metrics and reconciliation evidence.

Inputs: processed documents, sections, sentences, projected annotations.
Outputs: quality report and reconciliation metrics.
Parameters: quality rules version.
Validation gates: checksums, counts, offsets, quality status.
Failure behaviour: fail mandatory quality failures.
Observability: aggregate metrics only.
Security: no document text in logs.
Local mapping: `preprocessing.quality` and `preprocessing.reconciliation`.
