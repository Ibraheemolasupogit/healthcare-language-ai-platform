# Operational Event Integrity

Operational event integrity validates JSONL event structure, event versions,
checksums, duplicates, and malformed records. Malformed records are copied to a
local quarantine directory with a manifest for review.

Run:

```bash
python -m healthcare_language_ai operational-integrity --events-dir tests/fixtures/observability --output-dir reports/assurance/observability
```
