# Section And Sentence Processing

Section parsing uses deterministic heading rules for the controlled synthetic
templates. Unknown headings are retained as unknown rather than inferred from
meaning. Repeated headings are ordered by source position.

Sentence segmentation is lightweight and rule-based. It uses punctuation, line
boundaries, and section boundaries. It is not production-grade clinical sentence
segmentation and uses no statistical or ML model.

Offsets refer to `normalised_text` for processed sections and sentences.
