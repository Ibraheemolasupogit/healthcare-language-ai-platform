# Backup And Recovery

Milestone 11 adds deterministic backups for portfolio-critical local evidence:
configuration, schemas, API fixtures, RAG evidence, demo evidence, and portfolio
summaries. Restore is guarded so it cannot overwrite the active repository
unless an explicit destination is provided.

Run:

```bash
python -m healthcare_language_ai assurance-backup --profile portfolio-critical --output-root outputs/assurance/backups
python -m healthcare_language_ai assurance-backup-validate --backup-dir outputs/assurance/backups/<backup-id>
python -m healthcare_language_ai assurance-recovery-exercise --profile portfolio-critical --output-root reports/assurance/recovery
```
