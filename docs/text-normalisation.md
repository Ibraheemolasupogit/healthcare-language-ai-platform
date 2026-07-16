# Text Normalisation

Conservative mode applies Unicode NFC, LF line endings, tab expansion, trailing
space removal, controlled repeated-space reduction, and final-newline policy.

Analytical mode additionally creates a casefolded, whitespace-collapsed,
punctuation-normalised representation. It does not remove negation, digits,
measurement-like values, punctuation indiscriminately, or synthetic identifiers.

Every transformation records version, applied status, change count, and before
and after checksums. The output is not clinically corrected text.
