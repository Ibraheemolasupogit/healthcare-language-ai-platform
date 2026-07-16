# Preprocessing Architecture

Milestone 4 consumes validated ingestion evidence and writes deterministic local
preprocessing outputs.

```mermaid
flowchart LR
    A["Validated ingestion evidence"] --> B["Source validation"]
    B --> C["Text inspection and normalisation"]
    C --> D["Section parsing"]
    D --> E["Sentence segmentation"]
    E --> F["Token and quality metrics"]
    F --> G["Annotation projection"]
    G --> H["Manifest, reconciliation, Databricks plan"]
```

The pipeline preserves source text exactly and writes derived `normalised_text`
and optional `analytical_text` fields. Persisted timestamps use the configured
reference timestamp, not wall-clock time.
