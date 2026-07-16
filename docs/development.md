# Development

Milestone 12 development commands are exposed through Make targets such as
`portfolio-audit`, `traceability-build`, `architecture-pack`,
`release-readiness`, `release-manifest`, `release-package`,
`verify-portfolio-fixtures`, and `verify-release-fixtures`.

## Python Setup

Use Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Quality Commands

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest
make quality
```

## CLI Usage

```bash
python -m healthcare_language_ai version
python -m healthcare_language_ai config-show --config config/application.yaml
python -m healthcare_language_ai validate-environment
python -m healthcare_language_ai synthetic-generate --count 15 --seed 2026 --document-type all --reference-timestamp 2026-01-01T09:00:00+00:00 --output-dir outputs/synthetic
python -m healthcare_language_ai synthetic-validate --dataset-dir outputs/synthetic
python -m healthcare_language_ai synthetic-summary --dataset-dir outputs/synthetic
python -m healthcare_language_ai ingest-run --source-dir tests/fixtures/synthetic --output-root outputs/ingestion --mode strict --reference-timestamp 2026-01-02T09:00:00+00:00
python -m healthcare_language_ai ingest-validate --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203
python -m healthcare_language_ai ingest-summary --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203
python -m healthcare_language_ai snowflake-plan --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203
python -m healthcare_language_ai preprocess-run --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203 --output-root outputs/preprocessing --mode conservative --reference-timestamp 2026-01-03T09:00:00+00:00
python -m healthcare_language_ai preprocess-validate --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc
python -m healthcare_language_ai preprocess-summary --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc
python -m healthcare_language_ai databricks-plan --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc
```

## Docker Usage

```bash
docker build -t healthcare-language-ai-platform:milestone-1 .
docker run --rm healthcare-language-ai-platform:milestone-1
```

For Milestone 2 generation:

```bash
docker build -t healthcare-language-ai-platform:milestone-2 .
docker run --rm -v "$(pwd)/outputs:/app/outputs" healthcare-language-ai-platform:milestone-2 healthcare-language-ai synthetic-generate --count 10 --seed 2026 --output-dir /app/outputs/synthetic
docker build -t healthcare-language-ai-platform:milestone-3 .
docker run --rm -v "$(pwd)/tests/fixtures:/app/fixtures:ro" -v "$(pwd)/outputs:/app/outputs" healthcare-language-ai-platform:milestone-3 healthcare-language-ai ingest-run --source-dir /app/fixtures/synthetic --output-root /app/outputs/ingestion --mode strict --reference-timestamp 2026-01-02T09:00:00+00:00
docker build -t healthcare-language-ai-platform:milestone-4 .
docker run --rm -v "$(pwd)/tests/fixtures:/app/fixtures:ro" -v "$(pwd)/outputs:/app/outputs" healthcare-language-ai-platform:milestone-4 healthcare-language-ai preprocess-run --ingestion-dir /app/fixtures/ingestion/ING-92a15c8f10047400ee895203 --output-root /app/outputs/preprocessing --mode conservative --reference-timestamp 2026-01-03T09:00:00+00:00
```

## Configuration Precedence

Configuration is resolved from code defaults, optional YAML values, environment
variables, and optional `.env` values. Final precedence is code defaults, YAML,
optional `.env`, and environment variables. Environment variable names use the
`HEALTHCARE_LANGUAGE_AI_` prefix; nested synthetic settings use `__`.

## Contribution Conventions

Keep modules focused, type annotated, and import-safe. Add tests with behavior,
not just existence checks. Do not add real credentials or real clinical data.
## Milestone 5 Local Commands

Use `make extract-run`, `make extract-validate`, `make evaluate-run`,
`make evaluate-validate`, and `make mlflow-plan` for local baseline NLP evidence.
`make validate` includes extraction and evaluation fixture reproducibility.

## Milestone 6 Local Commands

Use `make index-build`, `make retrieval-run`, `make retrieval-evaluate`,
`make vector-search-plan`, and `make retrieval-mlflow-plan`. `make validate`
includes retrieval query, index, run, and evaluation fixture reproducibility.
## Milestone 7 Validation

Use `make validate` to run model-free retrieval-quality fixture checks. Optional local dense benchmarking is isolated behind `make embedding-benchmark-local LOCAL_MODEL_PATH=/absolute/path/to/local/model` and is not part of default CI.

## Milestone 9 Validation

Use `make verify-rag-query-fixtures`, `make verify-rag-run-fixtures`,
`make verify-rag-evaluation-fixtures`, `make rag-validate`, and
`make rag-approval` to validate guarded synthetic RAG evidence. These commands
do not require local LLM dependencies or network access.
