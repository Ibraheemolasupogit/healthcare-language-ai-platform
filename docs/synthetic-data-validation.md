# Synthetic Data Validation

## Data-Quality Rules

Validation checks required fields, unique synthetic identifiers, supported
document types, synthetic classification, non-empty text, maximum text length,
timezone-aware and chronological timestamps, valid annotation offsets, matching
manifest counts, matching file checksums, and duplicate canonical records.

## Privacy-Pattern Checks

Generated text is checked for NHS-number-like values, emails, UK telephone
numbers, postcodes, URLs, IPv4 addresses, credit-card-like numbers, National
Insurance-like values, and unapproved long numeric identifiers.

These regex checks are portfolio safeguards. They do not prove anonymisation and
are not a substitute for production de-identification or disclosure control.

## Clinical-Safety Wording Checks

Validation rejects auditable prohibited phrases such as `you should take`,
`start taking`, `stop taking`, `recommended treatment`, `medical advice`,
`diagnosis confirmed`, and `urgent treatment required`.

## Checksum Verification

The manifest stores SHA-256 checksums for the canonical document and annotation
JSONL files. The manifest does not checksum itself, avoiding circular hashing.

## Offset Validation

Every span annotation must satisfy `text[start:end] == value`.

## Failure Behaviour

Generation fails when mandatory invariants fail. CLI validation returns a
non-zero exit code when existing files do not pass validation.
