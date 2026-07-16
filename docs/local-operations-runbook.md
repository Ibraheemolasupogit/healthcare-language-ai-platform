# Local Operations Runbook

For a full local static validation pass:

```bash
make validate
```

For runtime smoke tests:

```bash
make runtime-smoke
```

For final portfolio assurance:

```bash
make portfolio-assurance
make portfolio-assurance-validate
make portfolio-assurance-summary
```

Known boundaries remain unchanged: synthetic data only, localhost defaults,
read-only API, no production authentication, no hosted models, no cloud
deployment, and no clinical use.
