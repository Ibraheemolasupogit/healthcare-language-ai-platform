# Entity Extraction Architecture

Milestone 5 consumes validated preprocessing evidence only. The local flow is:

```mermaid
flowchart LR
  A["Preprocessing fixture"] --> B["Vocabulary and rule loading"]
  B --> C["Exact phrase matching"]
  C --> D["Overlap resolution"]
  D --> E["Entity predictions"]
  A --> F["Heading-based classifier"]
  F --> G["Document classifications"]
  E --> H["Reconciliation and manifests"]
  G --> H
```

Inputs are `processed_documents`, `processed_sections`, `processed_sentences`, and
`projected_annotations`. Outputs preserve lineage to preprocessing and contain no
full-text summaries or logs.

