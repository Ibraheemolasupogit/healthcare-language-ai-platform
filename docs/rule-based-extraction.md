# Rule-Based Extraction

The baseline supports the controlled synthetic labels:
`administrative_priority`, `body_site`, `descriptor`, `encounter_context`,
`investigation`, `observation`, `presenting_concern`, `specialty`, and
`workflow_status`.

Rules use exact phrase matching over `normalised_text`, case-insensitive matching,
word boundaries, optional section constraints, deterministic priority ordering, and
audited overlap suppression. Confidence is rule-derived and is not a calibrated
clinical probability.

