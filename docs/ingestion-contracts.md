# Ingestion Contracts

Canonical documents flatten source document metadata while preserving lineage:
document ID, synthetic subject and encounter IDs, document type, source system,
classification, text, timestamps, generator/template/vocabulary versions,
source dataset details, source line number, source checksum, run ID, and
deterministic ingestion timestamp.

Canonical annotations are row-oriented. Span annotations retain offsets.
Document-level annotations use null offsets and are not forced into invalid text
spans.

CSV outputs use UTF-8, LF endings, header rows, deterministic column order, RFC
quoting, and empty strings for configured null values. Embedded clinical-text
line breaks are quoted by the Python CSV writer and round-trip through
`csv.DictReader`.

Parquet outputs use `pyarrow`, deterministic row ordering, no index column, and
configured compression. CSV and JSON are the byte-for-byte canonical evidence;
Parquet is validated for logical row count and schema equivalence.
