# 03 Parse Sections

Purpose: parse auditable synthetic section headings.

Inputs: processed documents.
Outputs: silver document sections.
Parameters: section parser version.
Validation gates: offset validity and deterministic section IDs.
Failure behaviour: warnings for missing headings, failures for invalid offsets.
Observability: section-label counts.
Security: synthetic data only.
Local mapping: `preprocessing.sections`.
