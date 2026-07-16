# Error Analysis

Error records are generated for false positives and false negatives. Each record
contains bounded synthetic context, a checksum, prediction or ground-truth lineage,
and an explicit likely reason. Full documents are not emitted in error summaries.

Supported error concepts include false positives, false negatives, boundary
mismatches, label mismatches, normalisation mismatches, and document-classification
errors.

