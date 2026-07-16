# Operational Observability

Milestone 10 writes safe local operational events for portfolio evidence. Events include request IDs, query checksums, low-cardinality categories, statuses, error codes, durations, timestamps, version, and environment.

Events exclude full query text, answer text, source document text, evidence text, credentials, personal data, document IDs as metric labels, subject IDs, and evidence IDs as metric labels.

Metric summaries distinguish canonical evaluation metrics from runtime operational counts. Prometheus-compatible output is local and does not require a Prometheus server.
