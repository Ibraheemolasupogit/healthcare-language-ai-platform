# Query Expansion

Query expansion is deterministic and local. It uses small auditable maps for controlled synonyms, abbreviations, section aliases, and safe variants from fixture language.

Every expansion records rule ID, original term, expanded term, expansion type, and version. Ambiguous abbreviations are not expanded automatically.

No LLMs, hosted terminology services, SNOMED CT, ICD-10 downloads, or external ontologies are used.
