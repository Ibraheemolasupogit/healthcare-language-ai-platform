# Ingestion Reconciliation

Reconciliation compares source manifest counts, loaded source counts, canonical
document and annotation counts, quarantine counts, document-type distribution,
annotation-label distribution, duplicate identifiers, orphan annotations,
checksum validation, schema validation, governance flags, and Snowflake plan
consistency.

Each metric records expected value, actual value, status, severity, and message.
The overall status is derived from metric statuses and is not hard-coded.

Strict mode fails on mandatory validation failures. Quarantine mode records
invalid records with source file, source line, record identifier, error code,
error category, sanitized message, payload checksum, and deterministic
quarantine timestamp.
