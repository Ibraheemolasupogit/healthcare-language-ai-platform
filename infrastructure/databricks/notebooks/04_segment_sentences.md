# 04 Segment Sentences

Purpose: run deterministic rule-based sentence segmentation.

Inputs: processed sections.
Outputs: silver document sentences.
Parameters: sentence segmenter version.
Validation gates: non-overlapping offsets and non-empty sentences.
Failure behaviour: fail invalid spans.
Observability: sentence counts and length warnings.
Security: no model dependencies.
Local mapping: `preprocessing.sentences`.
