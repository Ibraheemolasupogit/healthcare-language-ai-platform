# Annotation Projection

Source offsets from ingestion are preserved in projected annotation evidence.
When source and normalised text are unchanged, offsets are marked `unchanged`.
When a unique value match exists, offsets are marked `projected`. Ambiguous or
missing matches are `unresolved`. Document-level annotations are
`not_applicable`.

No projected offset is guessed. Every projected span must match target text.
