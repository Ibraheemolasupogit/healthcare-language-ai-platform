# Synthetic Data Schema

## Record Schema

`clinical_documents.jsonl` contains one JSON object per synthetic document with
document ID, document type, text, synthetic timestamps, source system,
classification, metadata, generator version, template version, vocabulary
version, seed, and record index.

## Annotation Schema

`document_annotations.jsonl` stores annotations separately from free text. Span
annotations include label, value, start, end, normalised value, and source.
Document-level metadata is used when an item has no natural text span.

## Manifest Schema

`dataset_manifest.json` records dataset name, versions, seed, reference
timestamp, counts, file list, SHA-256 checksums for canonical JSONL files,
schema version, synthetic-only status, and clinical-use prohibition.

## Quality-Report Schema

`data_quality_report.json` records validation status, structured checks, counts,
and safety flags.

## Versioning Strategy

Generator, template, vocabulary, dataset, and schema versions are explicit
constants. Later generation logic changes should update these deliberately.

## Example Sanitised Record

```json
{
  "document_id": "SYN-DOC-000001",
  "document_type": "clinical_note",
  "source_system": "synthetic_generator",
  "data_classification": "synthetic",
  "generator_version": "1.0.0",
  "template_version": "1.0.0",
  "vocabulary_version": "1.0.0"
}
```
