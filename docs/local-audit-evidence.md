# Local Audit Evidence

The event store is local portfolio operational evidence, not a regulatory audit log.

It records accepted queries, pre-retrieval refusals, retrieval abstentions, generated answers, validation statuses, promoted or rejected answers, and application errors. Events are append-only JSONL with small-file rotation and retention.
