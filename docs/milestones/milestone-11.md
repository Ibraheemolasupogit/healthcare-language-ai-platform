# Milestone 11: Local Platform Hardening

Milestone 11 hardens the local portfolio platform without changing its core
boundary: synthetic data only, localhost defaults, read-only API behaviour, no
hosted models, no cloud deployment, and no production authentication.

The milestone adds contract inventory and compatibility checks, configuration
assurance, FastAPI lifespan startup checks, local rate limiting, bounded
runtime smoke tests, operational event integrity checks, deterministic backup
and restore exercises, security and sensitive-content scanning, offline
dependency inventory, SBOM evidence, static container assurance, and final
portfolio assurance gates.

Primary commands:

```bash
python -m healthcare_language_ai contracts-validate --baseline-dir tests/fixtures/assurance/contracts/baseline
python -m healthcare_language_ai configuration-assurance --output-dir reports/assurance
python -m healthcare_language_ai operational-integrity --events-dir tests/fixtures/observability --output-dir reports/assurance/observability
python -m healthcare_language_ai assurance-recovery-exercise --profile portfolio-critical --output-root reports/assurance/recovery
python -m healthcare_language_ai security-assurance --output-dir reports/assurance
python -m healthcare_language_ai dependency-inventory --output-dir reports/assurance
python -m healthcare_language_ai sbom-generate --output-dir reports/assurance
python -m healthcare_language_ai container-assurance --dockerfile Dockerfile --output-dir reports/assurance
python -m healthcare_language_ai portfolio-assurance --output-dir reports/assurance
```

Runtime smoke tests are explicit and separate from `make validate`:

```bash
make runtime-smoke
```

Generated assurance evidence lives under `reports/assurance`,
`reports/runtime-smoke`, and `outputs/assurance`. Checked-in deterministic
fixtures live under `tests/fixtures/assurance`.
