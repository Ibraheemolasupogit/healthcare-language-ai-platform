# 07 Publish Silver Gold

Purpose: describe target-state publication from silver to gold contracts.

Inputs: silver preprocessing outputs.
Outputs: gold preprocessing summary and metric contracts.
Parameters: target catalog and schemas.
Validation gates: table contracts and quality gates.
Failure behaviour: stop before publication on failed reconciliation.
Observability: run and table counts.
Security: least-privilege target-state roles.
Local mapping: dry-run Databricks plan only.
