# Synthetic Benchmark Limitations

The extraction vocabulary intentionally overlaps with the synthetic generation
vocabulary. This can inflate scores because phrase forms and templates are familiar
to the rules.

The fixture is still useful for pipeline validation: it proves deterministic
loading, prediction contracts, offset integrity, metric arithmetic, manifests,
checksums, and dry-run experiment planning.

These metrics do not demonstrate real-world clinical performance, demographic
representativeness, external validity, diagnosis quality, or treatment safety.
Future work needs blind synthetic holdouts, adversarial examples, and expert review.

