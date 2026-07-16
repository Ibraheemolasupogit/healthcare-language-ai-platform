# Baseline Evaluation

Evaluation aligns predictions to projected Milestone 4 annotations in the same text
representation. Exact matching requires document, label, scope, start offset, and
end offset to match. Normalised-value and relaxed-overlap policies are represented
as versioned settings for future comparison.

Metrics include micro and macro precision, recall, F1, per-label metrics,
per-document-type metrics, document-classification accuracy, macro F1, and a
confusion matrix. Zero division returns `0.0`.

