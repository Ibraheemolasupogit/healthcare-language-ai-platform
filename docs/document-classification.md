# Document Classification

Document-type classification is heading based. It scores recognised section labels
against transparent rules for `clinical_note`, `discharge_summary`,
`referral_letter`, `radiology_report`, and `pathology_report`.

The classifier does not copy the source document-type field. Ties are resolved by
score and then lexicographic class name.

