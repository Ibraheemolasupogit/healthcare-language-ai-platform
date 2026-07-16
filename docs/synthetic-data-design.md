# Synthetic Data Design

## Purpose

Milestone 2 creates deterministic, fictional clinical-style text for future NLP
evaluation. The data is realistic enough for parsing and annotation tests, but
it is not clinically valid and must not be used for patient care.

## Design Principles

Generation is local, deterministic, auditable, and template-driven. It uses no
external APIs, no downloaded datasets, no real patient records, no names, no
addresses, and no real healthcare identifiers.

## Controlled Vocabulary Approach

Small versioned vocabulary lists live in code. They cover presenting concerns,
observations, body sites, investigations, encounter contexts, workflow statuses,
specialties, priorities, descriptors, and follow-up placeholders.

## Template Approach

Each supported document type has a distinct template: clinical note, discharge
summary, referral letter, radiology report, and pathology report. Templates use
fictional wording and avoid prescriptive clinical advice.

## Determinism

Generation uses local `random.Random` instances seeded with the run seed, record
index, document type, and generator version. Persisted outputs do not include
current wall-clock time.

## Reference Timestamp

The default reference timestamp is `2026-01-01T09:00:00+00:00`. CLI users may
override it with a timezone-aware ISO-8601 value.

## Identifier Design

Synthetic identifiers use approved prefixes such as `SYN-SUBJ-000001`,
`SYN-ENC-000001`, `SYN-DOC-000001`, and deterministic run identifiers. They do
not encode names, dates of birth, geography, NHS numbers, or medical-record
numbers.

## Future Use

Later milestones can use these fixtures to test ingestion, NLP extraction,
classification, embeddings, retrieval, and evaluation workflows.
