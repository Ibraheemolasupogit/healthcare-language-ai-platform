.PHONY: help install install-dev install-dense-local format format-check lint type-check test test-cov quality validate run synthetic-generate synthetic-validate synthetic-summary synthetic-fixtures verify-synthetic-fixtures ingest-run ingest-validate ingest-summary snowflake-plan ingestion-fixtures verify-ingestion-fixtures preprocess-run preprocess-validate preprocess-summary databricks-plan preprocessing-fixtures verify-preprocessing-fixtures extract-run extract-validate extract-summary extraction-fixtures verify-extraction-fixtures evaluate-run evaluate-validate evaluate-summary mlflow-plan evaluation-fixtures verify-evaluation-fixtures index-build index-validate index-summary retrieval-run retrieval-validate retrieval-summary retrieval-evaluate retrieval-evaluate-validate retrieval-evaluate-summary vector-search-plan retrieval-mlflow-plan retrieval-query-fixtures verify-retrieval-query-fixtures retrieval-index-fixtures verify-retrieval-index-fixtures retrieval-run-fixtures verify-retrieval-run-fixtures retrieval-evaluation-fixtures verify-retrieval-evaluation-fixtures retrieval-holdout-fixtures verify-retrieval-holdout-fixtures retrieval-quality-query-fixtures verify-retrieval-quality-query-fixtures retrieval-quality-experiment-fixtures verify-retrieval-quality-experiment-fixtures retrieval-quality-comparison-fixtures verify-retrieval-quality-comparison-fixtures retrieval-quality-validate retrieval-quality-summary retrieval-approval retrieval-review-pack retrieval-failure-fixtures verify-retrieval-failure-fixtures retrieval-judgment-audit retrieval-benchmark-upgrade verify-retrieval-remediation-benchmark retrieval-remediation-experiment-fixtures verify-retrieval-remediation-experiment-fixtures retrieval-remediation-comparison-fixtures verify-retrieval-remediation-comparison-fixtures retrieval-remediation-validate retrieval-remediation-summary retrieval-remediation-approval rag-query-fixtures verify-rag-query-fixtures rag-run-fixtures verify-rag-run-fixtures rag-evaluation-fixtures verify-rag-evaluation-fixtures rag-validate rag-summary rag-approval rag-trace rag-mlflow-plan rag-databricks-plan api-run api-validate api-contract-fixtures verify-api-contract-fixtures dashboard-run dashboard-validate demo-run demo-validate demo-fixtures verify-demo-fixtures operational-summary observability-validate portfolio-summary schemas-generate embedding-benchmark-local docker-build docker-run clean
.PHONY: contracts-inventory contracts-baseline contracts-compare contracts-validate verify-contract-baseline configuration-assurance operational-integrity operational-quarantine-summary assurance-backup assurance-backup-validate assurance-recovery-exercise security-assurance dependency-inventory sbom-generate container-assurance portfolio-assurance portfolio-assurance-validate portfolio-assurance-summary runtime-smoke runtime-smoke-api runtime-smoke-dashboard runtime-smoke-summary verify-assurance-compatibility-fixtures verify-assurance-security-fixtures portfolio-audit portfolio-audit-validate milestones-audit traceability-build traceability-validate architecture-pack architecture-validate capability-map technology-map role-alignment interview-pack demo-pack evidence-index evidence-index-validate run-registry portfolio-model-card documentation-validate repository-cleanliness repository-size-audit release-readiness release-readiness-validate release-manifest release-package release-package-validate portfolio-final-summary verify-portfolio-fixtures verify-release-fixtures

PYTHON ?= python3

help:
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z_-]+:.*## / {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package.
	$(PYTHON) -m pip install .

install-dev: ## Install development dependencies.
	$(PYTHON) -m pip install -r requirements-dev.txt

install-dense-local: ## Install optional local dense embedding dependencies.
	$(PYTHON) -m pip install ".[dense-local]"

format: ## Format source and tests with Ruff.
	$(PYTHON) -m ruff format .

format-check: ## Check formatting without modifying files.
	$(PYTHON) -m ruff format --check .

lint: ## Run Ruff lint checks.
	$(PYTHON) -m ruff check .

type-check: ## Run mypy over the src package.
	$(PYTHON) -m mypy src

test: ## Run tests.
	$(PYTHON) -m pytest

test-cov: ## Run tests with coverage.
	$(PYTHON) -m pytest --cov=healthcare_language_ai

quality: lint format-check type-check test ## Run non-mutating quality checks.

validate: quality ## Run quality checks and CLI environment validation.
	$(PYTHON) -m healthcare_language_ai validate-environment
	$(PYTHON) -m healthcare_language_ai synthetic-validate --dataset-dir tests/fixtures/synthetic
	$(PYTHON) -m healthcare_language_ai ingest-validate --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203
	$(PYTHON) -m healthcare_language_ai preprocess-validate --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc
	$(PYTHON) -m healthcare_language_ai extract-validate --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d
	$(PYTHON) -m healthcare_language_ai evaluate-validate --evaluation-dir tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605
	$(PYTHON) -m healthcare_language_ai index-validate --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9
	$(PYTHON) -m healthcare_language_ai retrieve-validate --retrieval-dir tests/fixtures/retrieval/runs/RET-f8cc230a729145594d08b389
	$(PYTHON) -m healthcare_language_ai retrieve-validate --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate-validate --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-e7f370442452fb045cd7d541
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate-validate --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b
	$(PYTHON) -m healthcare_language_ai snowflake-plan --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203
	$(PYTHON) -m healthcare_language_ai databricks-plan --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc
	$(PYTHON) -m healthcare_language_ai mlflow-plan --evaluation-dir tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605
	$(PYTHON) -m healthcare_language_ai vector-search-plan --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b
	$(PYTHON) -m healthcare_language_ai retrieval-mlflow-plan --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b
	$(PYTHON) -m healthcare_language_ai holdout-validate --holdout-dir tests/fixtures/retrieval-quality/holdout
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-validate --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-c9fa06f6b7d3543d0565dc53
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-validate --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-1666875e44ee447a43599994
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-validate --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-a9ba4097f51ac94abe4e5b2a
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-validate --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-b2e0796791634a3e5b1b65c6
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-validate --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-fb2b3ecba8151d28fa6f3f9a
	$(PYTHON) -m healthcare_language_ai retrieval-compare-validate --comparison-dir tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce
	$(PYTHON) -m healthcare_language_ai retrieval-approval --comparison-dir tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce
	$(PYTHON) -m healthcare_language_ai rag-validate --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874
	$(PYTHON) -m healthcare_language_ai rag-evaluate-validate --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017
	$(PYTHON) -m healthcare_language_ai rag-approval --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017
	$(PYTHON) -m healthcare_language_ai api-validate
	$(PYTHON) -m healthcare_language_ai dashboard-validate
	$(PYTHON) -m healthcare_language_ai system-readiness
	$(PYTHON) -m healthcare_language_ai operational-events-validate --events-dir tests/fixtures/observability
	$(PYTHON) -m healthcare_language_ai contracts-compare --baseline-dir tests/fixtures/assurance/contracts/baseline --output-dir reports/assurance/compatibility
	$(PYTHON) -m healthcare_language_ai contracts-validate --compatibility-dir reports/assurance/compatibility
	$(PYTHON) -m healthcare_language_ai configuration-assurance --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai operational-integrity --events-dir tests/fixtures/observability --output-dir reports/assurance/observability
	$(PYTHON) -m healthcare_language_ai assurance-backup-validate --backup-dir tests/fixtures/assurance/backup/BACKUP-b487bf0c20ada4ec0058d954
	$(PYTHON) -m healthcare_language_ai assurance-recovery-exercise --profile portfolio-critical --output-root reports/assurance/recovery
	$(PYTHON) -m healthcare_language_ai security-assurance --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai dependency-inventory --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai sbom-generate --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai container-assurance --dockerfile Dockerfile --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai portfolio-assurance --output-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai portfolio-assurance-validate --assurance-dir reports/assurance
	$(PYTHON) -m healthcare_language_ai demo-validate --demo-dir tests/fixtures/demo/DEMO-7d8d73b2b21ec496c6e47175
	$(PYTHON) -m healthcare_language_ai schemas-generate
	$(PYTHON) -m healthcare_language_ai architecture-pack --output-dir reports/portfolio/architecture
	$(PYTHON) -m healthcare_language_ai architecture-validate --architecture-dir reports/portfolio/architecture
	$(PYTHON) -m healthcare_language_ai interview-pack --output-dir docs/interview
	$(PYTHON) -m healthcare_language_ai demo-pack --output-dir docs/demo
	$(PYTHON) -m healthcare_language_ai portfolio-audit --output-dir reports/portfolio/audit
	$(PYTHON) -m healthcare_language_ai portfolio-audit-validate --audit-dir reports/portfolio/audit
	$(PYTHON) -m healthcare_language_ai milestones-audit --output-dir reports/portfolio/milestones
	$(PYTHON) -m healthcare_language_ai traceability-build --output-dir reports/portfolio/traceability
	$(PYTHON) -m healthcare_language_ai traceability-validate --traceability-dir reports/portfolio/traceability
	$(PYTHON) -m healthcare_language_ai capability-map --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai technology-map --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai role-alignment --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai evidence-index --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai evidence-index-validate --evidence-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai run-registry --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai portfolio-model-card --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai documentation-validate
	$(PYTHON) -m healthcare_language_ai repository-cleanliness
	$(PYTHON) -m healthcare_language_ai repository-size-audit --output-dir reports/portfolio
	$(PYTHON) -m healthcare_language_ai release-readiness --output-dir reports/release --reference-timestamp 2026-01-19T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai release-readiness-validate --readiness-dir reports/release
	$(PYTHON) -m healthcare_language_ai release-manifest --readiness-dir reports/release --output-dir reports/release --reference-timestamp 2026-01-20T09:00:00+00:00
	$(MAKE) verify-synthetic-fixtures
	$(MAKE) verify-ingestion-fixtures
	$(MAKE) verify-preprocessing-fixtures
	$(MAKE) verify-extraction-fixtures
	$(MAKE) verify-evaluation-fixtures
	$(MAKE) verify-retrieval-query-fixtures
	$(MAKE) verify-retrieval-index-fixtures
	$(MAKE) verify-retrieval-run-fixtures
	$(MAKE) verify-retrieval-evaluation-fixtures
	$(MAKE) verify-retrieval-holdout-fixtures
	$(MAKE) verify-retrieval-quality-query-fixtures
	$(MAKE) verify-retrieval-quality-experiment-fixtures
	$(MAKE) verify-retrieval-quality-comparison-fixtures
	$(MAKE) verify-retrieval-failure-fixtures
	$(MAKE) verify-retrieval-remediation-benchmark
	$(MAKE) verify-retrieval-remediation-experiment-fixtures
	$(MAKE) verify-retrieval-remediation-comparison-fixtures
	$(MAKE) verify-rag-query-fixtures
	$(MAKE) verify-rag-run-fixtures
	$(MAKE) verify-rag-evaluation-fixtures
	$(MAKE) verify-api-contract-fixtures
	$(MAKE) verify-demo-fixtures
	$(MAKE) verify-contract-baseline
	$(MAKE) verify-assurance-compatibility-fixtures
	$(MAKE) verify-assurance-security-fixtures
	$(MAKE) verify-portfolio-fixtures
	$(MAKE) verify-release-fixtures

run: ## Show CLI help.
	$(PYTHON) -m healthcare_language_ai --help

api-run: ## Run the local FastAPI service on localhost.
	$(PYTHON) -m healthcare_language_ai api-run --host 127.0.0.1 --port 8000

api-validate: ## Validate API contracts and readiness without starting a server.
	$(PYTHON) -m healthcare_language_ai api-validate

api-contract-fixtures: ## Regenerate checked-in API contract fixtures.
	$(PYTHON) -m healthcare_language_ai api-contract-fixtures --output-dir tests/fixtures/api

verify-api-contract-fixtures: ## Regenerate API fixtures in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai api-contract-fixtures --output-dir $$tmp_dir; diff -r tests/fixtures/api $$tmp_dir; rm -rf $$tmp_dir

dashboard-run: ## Run the local Streamlit dashboard.
	$(PYTHON) -m healthcare_language_ai dashboard-run --port 8501 --service-mode direct

dashboard-validate: ## Validate dashboard imports and shared service wiring.
	$(PYTHON) -m healthcare_language_ai dashboard-validate

demo-run: ## Run deterministic demo scenarios into reports/demo.
	$(PYTHON) -m healthcare_language_ai demo-run --scenario-set standard --output-dir reports/demo

demo-validate: ## Validate generated reports/demo evidence.
	$(PYTHON) -m healthcare_language_ai demo-validate --demo-dir reports/demo

demo-fixtures: ## Regenerate checked-in deterministic demo fixture.
	$(PYTHON) -m healthcare_language_ai demo-run --scenario-set standard --output-dir tests/fixtures/demo/DEMO-7d8d73b2b21ec496c6e47175

verify-demo-fixtures: ## Regenerate demo fixture in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai demo-run --scenario-set standard --output-dir $$tmp_dir; diff -r tests/fixtures/demo/DEMO-7d8d73b2b21ec496c6e47175 $$tmp_dir; rm -rf $$tmp_dir

operational-summary: ## Print local operational metric summary.
	$(PYTHON) -m healthcare_language_ai operational-summary --events-dir tests/fixtures/observability

observability-validate: ## Validate controlled observability fixtures.
	$(PYTHON) -m healthcare_language_ai operational-events-validate --events-dir tests/fixtures/observability

portfolio-summary: ## Generate local portfolio evidence summary.
	$(PYTHON) -m healthcare_language_ai portfolio-summary --output-dir reports/portfolio

portfolio-audit: ## Generate final repository audit evidence.
	$(PYTHON) -m healthcare_language_ai portfolio-audit --output-dir reports/portfolio/audit

portfolio-audit-validate: ## Validate final repository audit evidence.
	$(PYTHON) -m healthcare_language_ai portfolio-audit-validate --audit-dir reports/portfolio/audit

milestones-audit: ## Generate final milestone completeness audit.
	$(PYTHON) -m healthcare_language_ai milestones-audit --output-dir reports/portfolio/milestones

traceability-build: ## Generate cross-milestone traceability evidence.
	$(PYTHON) -m healthcare_language_ai traceability-build --output-dir reports/portfolio/traceability

traceability-validate: ## Validate cross-milestone traceability evidence.
	$(PYTHON) -m healthcare_language_ai traceability-validate --traceability-dir reports/portfolio/traceability

architecture-pack: ## Generate final architecture evidence pack.
	$(PYTHON) -m healthcare_language_ai architecture-pack --output-dir reports/portfolio/architecture

architecture-validate: ## Validate final architecture evidence pack.
	$(PYTHON) -m healthcare_language_ai architecture-validate --architecture-dir reports/portfolio/architecture

capability-map: ## Generate final capability map.
	$(PYTHON) -m healthcare_language_ai capability-map --output-dir reports/portfolio

technology-map: ## Generate final technology map.
	$(PYTHON) -m healthcare_language_ai technology-map --output-dir reports/portfolio

role-alignment: ## Generate role and success-profile alignment evidence.
	$(PYTHON) -m healthcare_language_ai role-alignment --output-dir reports/portfolio

interview-pack: ## Generate reviewer interview evidence pack.
	$(PYTHON) -m healthcare_language_ai interview-pack --output-dir docs/interview

demo-pack: ## Generate reviewer demonstration guides.
	$(PYTHON) -m healthcare_language_ai demo-pack --output-dir docs/demo

evidence-index: ## Generate final portfolio evidence index.
	$(PYTHON) -m healthcare_language_ai evidence-index --output-dir reports/portfolio

evidence-index-validate: ## Validate final portfolio evidence index.
	$(PYTHON) -m healthcare_language_ai evidence-index-validate --evidence-dir reports/portfolio

run-registry: ## Generate final run and approval registry.
	$(PYTHON) -m healthcare_language_ai run-registry --output-dir reports/portfolio

portfolio-model-card: ## Generate final portfolio model card.
	$(PYTHON) -m healthcare_language_ai portfolio-model-card --output-dir reports/portfolio

documentation-validate: ## Validate reviewer-facing documentation.
	$(PYTHON) -m healthcare_language_ai documentation-validate

repository-cleanliness: ## Remove disposable local artifacts and report cleanliness.
	$(PYTHON) -m healthcare_language_ai repository-cleanliness

repository-size-audit: ## Audit repository size and prohibited model weights.
	$(PYTHON) -m healthcare_language_ai repository-size-audit --output-dir reports/portfolio

release-readiness: ## Generate final release-readiness report.
	$(PYTHON) -m healthcare_language_ai release-readiness --output-dir reports/release --reference-timestamp 2026-01-19T09:00:00+00:00

release-readiness-validate: ## Validate final release-readiness report.
	$(PYTHON) -m healthcare_language_ai release-readiness-validate --readiness-dir reports/release

release-manifest: ## Generate final release manifest.
	$(PYTHON) -m healthcare_language_ai release-manifest --readiness-dir reports/release --output-dir reports/release --reference-timestamp 2026-01-20T09:00:00+00:00

release-package: ## Create local reviewer-facing release package.
	$(PYTHON) -m healthcare_language_ai release-package --readiness-dir reports/release --output-root outputs/portfolio-release --reference-timestamp 2026-01-20T09:00:00+00:00

release-package-validate: ## Validate the latest local reviewer-facing release package.
	package_dir=outputs/portfolio-release/$$(python3 -c "import json; print(json.load(open('reports/release/release-manifest.json'))['release_id'])"); $(PYTHON) -m healthcare_language_ai release-package-validate --package-dir $$package_dir

portfolio-final-summary: ## Print final portfolio release summary.
	$(PYTHON) -m healthcare_language_ai portfolio-final-summary

verify-portfolio-fixtures: ## Regenerate M12 portfolio fixtures in /tmp and compare.
	set -e; tmp_dir=$$(mktemp -d); trap 'rm -rf "$$tmp_dir"' EXIT; $(PYTHON) -m healthcare_language_ai portfolio-audit --output-dir $$tmp_dir/audit; $(PYTHON) -m healthcare_language_ai milestones-audit --output-dir $$tmp_dir/milestones; $(PYTHON) -m healthcare_language_ai traceability-build --output-dir $$tmp_dir/traceability; $(PYTHON) -m healthcare_language_ai evidence-index --output-dir $$tmp_dir; $(PYTHON) -m healthcare_language_ai run-registry --output-dir $$tmp_dir; diff -r tests/fixtures/portfolio/repository-audit $$tmp_dir/audit; diff -r tests/fixtures/portfolio/milestone-audit $$tmp_dir/milestones; diff -r tests/fixtures/portfolio/traceability $$tmp_dir/traceability; diff tests/fixtures/portfolio/evidence-index/evidence-index.json $$tmp_dir/evidence-index.json; diff tests/fixtures/portfolio/evidence-index/evidence-index.md $$tmp_dir/evidence-index.md; diff tests/fixtures/portfolio/run-registry/run-registry.json $$tmp_dir/run-registry.json; diff tests/fixtures/portfolio/run-registry/run-registry.md $$tmp_dir/run-registry.md

verify-release-fixtures: ## Regenerate M12 release fixtures in /tmp and compare.
	set -e; tmp_dir=$$(mktemp -d); trap 'rm -rf "$$tmp_dir"' EXIT; $(PYTHON) -m healthcare_language_ai release-readiness --output-dir $$tmp_dir/release --reference-timestamp 2026-01-19T09:00:00+00:00; $(PYTHON) -m healthcare_language_ai release-manifest --readiness-dir $$tmp_dir/release --output-dir $$tmp_dir/release --reference-timestamp 2026-01-20T09:00:00+00:00; diff tests/fixtures/portfolio/release-readiness/release-readiness.json $$tmp_dir/release/release-readiness.json; diff tests/fixtures/portfolio/release-readiness/release-readiness.md $$tmp_dir/release/release-readiness.md; diff tests/fixtures/portfolio/release-manifest/release-manifest.json $$tmp_dir/release/release-manifest.json

schemas-generate: ## Generate JSON Schema files for M10 contracts.
	$(PYTHON) -m healthcare_language_ai schemas-generate

contracts-inventory: ## Generate the current local contract inventory.
	$(PYTHON) -m healthcare_language_ai contracts-inventory --output-dir reports/assurance/contracts/current

contracts-baseline: ## Regenerate the checked-in Milestone 11 contract baseline.
	$(PYTHON) -m healthcare_language_ai contracts-baseline --confirm-baseline-update --output-dir tests/fixtures/assurance/contracts/baseline

contracts-compare: ## Compare current contracts against the checked-in baseline.
	$(PYTHON) -m healthcare_language_ai contracts-compare --baseline-dir tests/fixtures/assurance/contracts/baseline --output-dir reports/assurance/compatibility

contracts-validate: ## Validate current contracts against the checked-in baseline.
	$(PYTHON) -m healthcare_language_ai contracts-compare --baseline-dir tests/fixtures/assurance/contracts/baseline --output-dir reports/assurance/compatibility
	$(PYTHON) -m healthcare_language_ai contracts-validate --compatibility-dir reports/assurance/compatibility

verify-contract-baseline: ## Regenerate the contract baseline in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai contracts-baseline --confirm-baseline-update --output-dir $$tmp_dir; diff -r tests/fixtures/assurance/contracts/baseline $$tmp_dir; rm -rf $$tmp_dir

configuration-assurance: ## Run local configuration hardening assurance.
	$(PYTHON) -m healthcare_language_ai configuration-assurance --output-dir reports/assurance

operational-integrity: ## Validate local operational event integrity and quarantine handling.
	$(PYTHON) -m healthcare_language_ai operational-integrity --events-dir tests/fixtures/observability --output-dir reports/assurance/observability

operational-quarantine-summary: ## Summarize quarantined operational events.
	$(PYTHON) -m healthcare_language_ai operational-quarantine-summary --quarantine-dir outputs/observability/quarantine

assurance-backup: ## Create a deterministic portfolio-critical evidence backup.
	$(PYTHON) -m healthcare_language_ai assurance-backup --profile portfolio-critical --output-root outputs/assurance/backups

assurance-backup-validate: ## Validate the checked-in assurance backup fixture.
	$(PYTHON) -m healthcare_language_ai assurance-backup-validate --backup-dir tests/fixtures/assurance/backup/BACKUP-b487bf0c20ada4ec0058d954

assurance-recovery-exercise: ## Run local backup and restore recovery exercise.
	$(PYTHON) -m healthcare_language_ai assurance-recovery-exercise --profile portfolio-critical --output-root reports/assurance/recovery

security-assurance: ## Run local security, secret, and sensitive-content assurance.
	$(PYTHON) -m healthcare_language_ai security-assurance --output-dir reports/assurance

dependency-inventory: ## Generate local dependency inventory and policy results.
	$(PYTHON) -m healthcare_language_ai dependency-inventory --output-dir reports/assurance

sbom-generate: ## Generate local SBOM-style dependency evidence.
	$(PYTHON) -m healthcare_language_ai sbom-generate --output-dir reports/assurance

container-assurance: ## Run static Dockerfile assurance checks.
	$(PYTHON) -m healthcare_language_ai container-assurance --dockerfile Dockerfile --output-dir reports/assurance

portfolio-assurance: ## Generate the Milestone 11 portfolio assurance decision.
	$(PYTHON) -m healthcare_language_ai portfolio-assurance --output-dir reports/assurance

portfolio-assurance-validate: ## Validate the Milestone 11 portfolio assurance decision.
	$(PYTHON) -m healthcare_language_ai portfolio-assurance-validate --assurance-dir reports/assurance

portfolio-assurance-summary: ## Print the Milestone 11 portfolio assurance summary.
	$(PYTHON) -m healthcare_language_ai portfolio-assurance-summary --assurance-dir reports/assurance

runtime-smoke: runtime-smoke-api runtime-smoke-dashboard runtime-smoke-summary ## Run bounded local runtime smoke checks.

runtime-smoke-api: ## Start and smoke-test the local FastAPI service.
	$(PYTHON) -m healthcare_language_ai runtime-smoke-api --host 127.0.0.1 --port 0 --timeout 30 --output-dir reports/runtime-smoke

runtime-smoke-dashboard: ## Start and smoke-test the local Streamlit dashboard.
	$(PYTHON) -m healthcare_language_ai runtime-smoke-dashboard --host 127.0.0.1 --port 0 --timeout 45 --output-dir reports/runtime-smoke

runtime-smoke-summary: ## Print runtime smoke report statuses.
	$(PYTHON) -m healthcare_language_ai runtime-smoke-summary --smoke-dir reports/runtime-smoke

verify-assurance-compatibility-fixtures: ## Regenerate compatibility fixture in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai contracts-compare --baseline-dir tests/fixtures/assurance/contracts/baseline --output-dir $$tmp_dir; diff -r tests/fixtures/assurance/compatibility/COMPAT-4f53cda18c2baa0c0354bb5f $$tmp_dir; rm -rf $$tmp_dir

verify-assurance-security-fixtures: ## Regenerate security fixture in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai security-assurance --output-dir $$tmp_dir; cp $$tmp_dir/security-control-report.json $$tmp_dir/security-control-results.json; cp reports/assurance/dependency-policy-results.json $$tmp_dir/dependency-policy-results.json; printf '# Security Assurance Fixture\n\nDeterministic local M11 security and dependency-policy fixture.\n' > $$tmp_dir/README.md; diff -r tests/fixtures/assurance/security $$tmp_dir; rm -rf $$tmp_dir

synthetic-generate: ## Generate the default synthetic dataset under outputs/synthetic.
	$(PYTHON) -m healthcare_language_ai synthetic-generate --count 15 --seed 2026 --document-type all --reference-timestamp 2026-01-01T09:00:00+00:00 --output-dir outputs/synthetic

synthetic-validate: ## Validate the default synthetic output dataset.
	$(PYTHON) -m healthcare_language_ai synthetic-validate --dataset-dir outputs/synthetic

synthetic-summary: ## Print a sanitized summary of the default synthetic output dataset.
	$(PYTHON) -m healthcare_language_ai synthetic-summary --dataset-dir outputs/synthetic

synthetic-fixtures: ## Regenerate checked-in deterministic synthetic fixtures.
	$(PYTHON) -m healthcare_language_ai synthetic-generate --count 15 --seed 2026 --document-type all --reference-timestamp 2026-01-01T09:00:00+00:00 --output-dir tests/fixtures/synthetic

verify-synthetic-fixtures: ## Regenerate fixtures in /tmp and compare byte-for-byte.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai synthetic-generate --count 15 --seed 2026 --document-type all --reference-timestamp 2026-01-01T09:00:00+00:00 --output-dir $$tmp_dir; diff -r tests/fixtures/synthetic $$tmp_dir; rm -rf $$tmp_dir

ingest-run: ## Run deterministic ingestion into outputs/ingestion.
	$(PYTHON) -m healthcare_language_ai ingest-run --source-dir tests/fixtures/synthetic --output-root outputs/ingestion --mode strict --reference-timestamp 2026-01-02T09:00:00+00:00 --overwrite-policy force_replace

ingest-validate: ## Validate the default checked-in ingestion fixture.
	$(PYTHON) -m healthcare_language_ai ingest-validate --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203

ingest-summary: ## Print a safe summary of the checked-in ingestion fixture.
	$(PYTHON) -m healthcare_language_ai ingest-summary --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203

snowflake-plan: ## Validate and summarize the Snowflake dry-run load plan.
	$(PYTHON) -m healthcare_language_ai snowflake-plan --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203

ingestion-fixtures: ## Regenerate checked-in deterministic ingestion fixtures.
	$(PYTHON) -m healthcare_language_ai ingest-run --source-dir tests/fixtures/synthetic --output-root tests/fixtures/ingestion --mode strict --reference-timestamp 2026-01-02T09:00:00+00:00 --overwrite-policy force_replace

verify-ingestion-fixtures: ## Regenerate ingestion fixture in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai ingest-run --source-dir tests/fixtures/synthetic --output-root $$tmp_dir --mode strict --reference-timestamp 2026-01-02T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/ingestion/ING-92a15c8f10047400ee895203 $$tmp_dir/ING-92a15c8f10047400ee895203; rm -rf $$tmp_dir

preprocess-run: ## Run deterministic preprocessing into outputs/preprocessing.
	$(PYTHON) -m healthcare_language_ai preprocess-run --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203 --output-root outputs/preprocessing --mode conservative --reference-timestamp 2026-01-03T09:00:00+00:00 --overwrite-policy force_replace

preprocess-validate: ## Validate the checked-in preprocessing fixture.
	$(PYTHON) -m healthcare_language_ai preprocess-validate --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc

preprocess-summary: ## Print a safe summary of the preprocessing fixture.
	$(PYTHON) -m healthcare_language_ai preprocess-summary --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc

databricks-plan: ## Validate and summarize the Databricks dry-run plan.
	$(PYTHON) -m healthcare_language_ai databricks-plan --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc

preprocessing-fixtures: ## Regenerate checked-in deterministic preprocessing fixtures.
	$(PYTHON) -m healthcare_language_ai preprocess-run --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203 --output-root tests/fixtures/preprocessing --mode conservative --reference-timestamp 2026-01-03T09:00:00+00:00 --overwrite-policy force_replace

verify-preprocessing-fixtures: ## Regenerate preprocessing fixture in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai preprocess-run --ingestion-dir tests/fixtures/ingestion/ING-92a15c8f10047400ee895203 --output-root $$tmp_dir --mode conservative --reference-timestamp 2026-01-03T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc $$tmp_dir/PRE-72e9829c61769cea948faacc; rm -rf $$tmp_dir

extract-run: ## Run deterministic extraction into outputs/extraction.
	$(PYTHON) -m healthcare_language_ai extract-run --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root outputs/extraction --text-representation normalised_text --reference-timestamp 2026-01-04T09:00:00+00:00 --overwrite-policy force_replace

extract-validate: ## Validate the checked-in extraction fixture.
	$(PYTHON) -m healthcare_language_ai extract-validate --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d

extract-summary: ## Print a safe summary of the extraction fixture.
	$(PYTHON) -m healthcare_language_ai extract-summary --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d

extraction-fixtures: ## Regenerate checked-in deterministic extraction fixtures.
	$(PYTHON) -m healthcare_language_ai extract-run --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root tests/fixtures/extraction --text-representation normalised_text --reference-timestamp 2026-01-04T09:00:00+00:00 --overwrite-policy force_replace

verify-extraction-fixtures: ## Regenerate extraction fixture in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai extract-run --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root $$tmp_dir --text-representation normalised_text --reference-timestamp 2026-01-04T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d $$tmp_dir/EXT-723871c87dfd1f3a3bb89b8d; rm -rf $$tmp_dir

evaluate-run: ## Run deterministic evaluation into outputs/evaluation.
	$(PYTHON) -m healthcare_language_ai evaluate-run --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root outputs/evaluation --matching-policy exact --reference-timestamp 2026-01-05T09:00:00+00:00 --overwrite-policy force_replace

evaluate-validate: ## Validate the checked-in evaluation fixture.
	$(PYTHON) -m healthcare_language_ai evaluate-validate --evaluation-dir tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605

evaluate-summary: ## Print a safe summary of the evaluation fixture.
	$(PYTHON) -m healthcare_language_ai evaluate-summary --evaluation-dir tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605

mlflow-plan: ## Validate and summarize the MLflow dry-run plan.
	$(PYTHON) -m healthcare_language_ai mlflow-plan --evaluation-dir tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605

evaluation-fixtures: ## Regenerate checked-in deterministic evaluation fixtures.
	$(PYTHON) -m healthcare_language_ai evaluate-run --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root tests/fixtures/evaluation --matching-policy exact --reference-timestamp 2026-01-05T09:00:00+00:00 --overwrite-policy force_replace

verify-evaluation-fixtures: ## Regenerate evaluation fixture in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai evaluate-run --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-root $$tmp_dir --matching-policy exact --reference-timestamp 2026-01-05T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/evaluation/EVAL-a56c0ad131cdbb85a69e1605 $$tmp_dir/EVAL-a56c0ad131cdbb85a69e1605; rm -rf $$tmp_dir

index-build: ## Build the default retrieval index.
	$(PYTHON) -m healthcare_language_ai index-build --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --output-root outputs/retrieval/indexes --unit-type all --embedding-provider deterministic_hash --reference-timestamp 2026-01-06T09:00:00+00:00 --overwrite-policy force_replace

index-validate: ## Validate the checked-in retrieval index fixture.
	$(PYTHON) -m healthcare_language_ai index-validate --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9

index-summary: ## Print a safe retrieval index summary.
	$(PYTHON) -m healthcare_language_ai index-summary --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9

retrieval-run: ## Run default hybrid retrieval.
	$(PYTHON) -m healthcare_language_ai retrieve-run --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 --query-set tests/fixtures/retrieval/queries/retrieval_queries.jsonl --output-root outputs/retrieval/runs --strategy hybrid --top-k 5 --reference-timestamp 2026-01-07T09:00:00+00:00 --overwrite-policy force_replace

retrieval-validate: ## Validate the checked-in hybrid retrieval fixture.
	$(PYTHON) -m healthcare_language_ai retrieve-validate --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296

retrieval-summary: ## Print a safe hybrid retrieval summary.
	$(PYTHON) -m healthcare_language_ai retrieve-summary --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296

retrieval-evaluate: ## Evaluate the checked-in hybrid retrieval fixture.
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296 --relevance-judgments tests/fixtures/retrieval/queries/relevance_judgments.jsonl --output-root outputs/retrieval/evaluation --k-values 1,3,5,10 --reference-timestamp 2026-01-08T09:00:00+00:00 --overwrite-policy force_replace

retrieval-evaluate-validate: ## Validate the checked-in hybrid retrieval evaluation fixture.
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate-validate --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b

retrieval-evaluate-summary: ## Print a safe hybrid retrieval evaluation summary.
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate-summary --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b

vector-search-plan: ## Validate and summarize the vector-search dry-run plan.
	$(PYTHON) -m healthcare_language_ai vector-search-plan --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b

retrieval-mlflow-plan: ## Validate and summarize the retrieval MLflow dry-run plan.
	$(PYTHON) -m healthcare_language_ai retrieval-mlflow-plan --evaluation-dir tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b

retrieval-query-fixtures: ## Regenerate checked-in retrieval query fixtures.
	$(PYTHON) -m healthcare_language_ai retrieval-query-fixtures --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-dir tests/fixtures/retrieval/queries

verify-retrieval-query-fixtures: ## Regenerate retrieval queries in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-query-fixtures --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --output-dir $$tmp_dir; diff -r tests/fixtures/retrieval/queries $$tmp_dir; rm -rf $$tmp_dir

retrieval-index-fixtures: ## Regenerate checked-in retrieval index fixture.
	$(PYTHON) -m healthcare_language_ai index-build --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --output-root tests/fixtures/retrieval/indexes --unit-type all --embedding-provider deterministic_hash --reference-timestamp 2026-01-06T09:00:00+00:00 --overwrite-policy force_replace

verify-retrieval-index-fixtures: ## Regenerate retrieval index in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai index-build --preprocessing-dir tests/fixtures/preprocessing/PRE-72e9829c61769cea948faacc --extraction-dir tests/fixtures/extraction/EXT-723871c87dfd1f3a3bb89b8d --output-root $$tmp_dir --unit-type all --embedding-provider deterministic_hash --reference-timestamp 2026-01-06T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 $$tmp_dir/IDX-364c8b97f9ad74ecea7444a9; rm -rf $$tmp_dir

retrieval-run-fixtures: ## Regenerate checked-in BM25 and hybrid retrieval run fixtures.
	$(PYTHON) -m healthcare_language_ai retrieve-run --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 --query-set tests/fixtures/retrieval/queries/retrieval_queries.jsonl --output-root tests/fixtures/retrieval/runs --strategy bm25 --top-k 5 --reference-timestamp 2026-01-07T09:00:00+00:00 --overwrite-policy force_replace
	$(PYTHON) -m healthcare_language_ai retrieve-run --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 --query-set tests/fixtures/retrieval/queries/retrieval_queries.jsonl --output-root tests/fixtures/retrieval/runs --strategy hybrid --top-k 5 --reference-timestamp 2026-01-07T09:00:00+00:00 --overwrite-policy force_replace

verify-retrieval-run-fixtures: ## Regenerate retrieval run fixtures in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieve-run --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 --query-set tests/fixtures/retrieval/queries/retrieval_queries.jsonl --output-root $$tmp_dir --strategy bm25 --top-k 5 --reference-timestamp 2026-01-07T09:00:00+00:00 --overwrite-policy force_replace; $(PYTHON) -m healthcare_language_ai retrieve-run --index-dir tests/fixtures/retrieval/indexes/IDX-364c8b97f9ad74ecea7444a9 --query-set tests/fixtures/retrieval/queries/retrieval_queries.jsonl --output-root $$tmp_dir --strategy hybrid --top-k 5 --reference-timestamp 2026-01-07T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/retrieval/runs/RET-f8cc230a729145594d08b389 $$tmp_dir/RET-f8cc230a729145594d08b389; diff -r tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296 $$tmp_dir/RET-864c03959a1c33a50926b296; rm -rf $$tmp_dir

retrieval-evaluation-fixtures: ## Regenerate checked-in retrieval evaluation fixtures.
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate --retrieval-dir tests/fixtures/retrieval/runs/RET-f8cc230a729145594d08b389 --relevance-judgments tests/fixtures/retrieval/queries/relevance_judgments.jsonl --output-root tests/fixtures/retrieval/evaluation --k-values 1,3,5,10 --reference-timestamp 2026-01-08T09:00:00+00:00 --overwrite-policy force_replace
	$(PYTHON) -m healthcare_language_ai retrieval-evaluate --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296 --relevance-judgments tests/fixtures/retrieval/queries/relevance_judgments.jsonl --output-root tests/fixtures/retrieval/evaluation --k-values 1,3,5,10 --reference-timestamp 2026-01-08T09:00:00+00:00 --overwrite-policy force_replace

verify-retrieval-evaluation-fixtures: ## Regenerate retrieval evaluation fixtures in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-evaluate --retrieval-dir tests/fixtures/retrieval/runs/RET-f8cc230a729145594d08b389 --relevance-judgments tests/fixtures/retrieval/queries/relevance_judgments.jsonl --output-root $$tmp_dir --k-values 1,3,5,10 --reference-timestamp 2026-01-08T09:00:00+00:00 --overwrite-policy force_replace; $(PYTHON) -m healthcare_language_ai retrieval-evaluate --retrieval-dir tests/fixtures/retrieval/runs/RET-864c03959a1c33a50926b296 --relevance-judgments tests/fixtures/retrieval/queries/relevance_judgments.jsonl --output-root $$tmp_dir --k-values 1,3,5,10 --reference-timestamp 2026-01-08T09:00:00+00:00 --overwrite-policy force_replace; diff -r tests/fixtures/retrieval/evaluation/RETEVAL-e7f370442452fb045cd7d541 $$tmp_dir/RETEVAL-e7f370442452fb045cd7d541; diff -r tests/fixtures/retrieval/evaluation/RETEVAL-7ca00cad930651cbf7a6881b $$tmp_dir/RETEVAL-7ca00cad930651cbf7a6881b; rm -rf $$tmp_dir

retrieval-holdout-fixtures: ## Regenerate checked-in retrieval holdout fixture.
	$(PYTHON) -m healthcare_language_ai holdout-generate --count 40 --seed 7026 --output-dir tests/fixtures/retrieval-quality/holdout --reference-timestamp 2026-01-09T09:00:00+00:00

verify-retrieval-holdout-fixtures: ## Regenerate retrieval holdout in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai holdout-generate --count 40 --seed 7026 --output-dir $$tmp_dir --reference-timestamp 2026-01-09T09:00:00+00:00; diff -r tests/fixtures/retrieval-quality/holdout $$tmp_dir; rm -rf $$tmp_dir

retrieval-quality-query-fixtures: ## Regenerate checked-in retrieval-quality benchmark fixture.
	$(PYTHON) -m healthcare_language_ai retrieval-quality-query-fixtures --output-dir tests/fixtures/retrieval-quality/benchmark --holdout-dir tests/fixtures/retrieval-quality/holdout

verify-retrieval-quality-query-fixtures: ## Regenerate retrieval-quality benchmark in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-quality-query-fixtures --output-dir $$tmp_dir --holdout-dir tests/fixtures/retrieval-quality/holdout; diff -r tests/fixtures/retrieval-quality/benchmark $$tmp_dir; rm -rf $$tmp_dir

retrieval-quality-experiment-fixtures: ## Regenerate checked-in model-free retrieval-quality experiments.
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id bm25_v2 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root tests/fixtures/retrieval-quality/experiments --reference-timestamp 2026-01-10T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id query_expanded_bm25_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root tests/fixtures/retrieval-quality/experiments --reference-timestamp 2026-01-10T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id negation_numeric_bm25_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root tests/fixtures/retrieval-quality/experiments --reference-timestamp 2026-01-10T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id cross_granularity_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root tests/fixtures/retrieval-quality/experiments --reference-timestamp 2026-01-10T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id feature_reranked_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root tests/fixtures/retrieval-quality/experiments --reference-timestamp 2026-01-10T09:00:00+00:00

verify-retrieval-quality-experiment-fixtures: ## Regenerate retrieval-quality experiments in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id bm25_v2 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root $$tmp_dir --reference-timestamp 2026-01-10T09:00:00+00:00; $(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id query_expanded_bm25_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root $$tmp_dir --reference-timestamp 2026-01-10T09:00:00+00:00; $(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id negation_numeric_bm25_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root $$tmp_dir --reference-timestamp 2026-01-10T09:00:00+00:00; $(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id cross_granularity_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root $$tmp_dir --reference-timestamp 2026-01-10T09:00:00+00:00; $(PYTHON) -m healthcare_language_ai retrieval-benchmark-run --configuration-id feature_reranked_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-root $$tmp_dir --reference-timestamp 2026-01-10T09:00:00+00:00; diff -r tests/fixtures/retrieval-quality/experiments $$tmp_dir; rm -rf $$tmp_dir

retrieval-quality-comparison-fixtures: ## Regenerate checked-in retrieval-quality comparison fixture.
	$(PYTHON) -m healthcare_language_ai retrieval-compare --benchmark-dir tests/fixtures/retrieval-quality/benchmark --configuration-registry config/retrieval-configurations.yaml --output-root tests/fixtures/retrieval-quality/comparison --reference-timestamp 2026-01-11T09:00:00+00:00

verify-retrieval-quality-comparison-fixtures: ## Regenerate retrieval-quality comparison in /tmp and compare deterministic files.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-compare --benchmark-dir tests/fixtures/retrieval-quality/benchmark --configuration-registry config/retrieval-configurations.yaml --output-root $$tmp_dir --reference-timestamp 2026-01-11T09:00:00+00:00; diff -r tests/fixtures/retrieval-quality/comparison $$tmp_dir; rm -rf $$tmp_dir

retrieval-quality-validate: ## Validate Milestone 7 retrieval-quality fixtures.
	$(PYTHON) -m healthcare_language_ai holdout-validate --holdout-dir tests/fixtures/retrieval-quality/holdout
	$(PYTHON) -m healthcare_language_ai retrieval-compare-validate --comparison-dir tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce

retrieval-quality-summary: ## Summarize Milestone 7 retrieval-quality fixtures.
	$(PYTHON) -m healthcare_language_ai holdout-summary --holdout-dir tests/fixtures/retrieval-quality/holdout
	$(PYTHON) -m healthcare_language_ai retrieval-compare-summary --comparison-dir tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce

retrieval-approval: ## Print Milestone 7 retrieval approval decision.
	$(PYTHON) -m healthcare_language_ai retrieval-approval --comparison-dir tests/fixtures/retrieval-quality/comparison/RETCOMP-11dee1c6ea11ed7908dff7ce

retrieval-review-pack: ## Generate synthetic relevance-review pack.
	$(PYTHON) -m healthcare_language_ai retrieval-review-pack --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-dir reports/retrieval-review

retrieval-failure-fixtures: ## Regenerate Milestone 8 failure inventory fixtures.
	$(PYTHON) -m healthcare_language_ai retrieval-failure-analyse --benchmark-dir tests/fixtures/retrieval-quality/benchmark --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-fb2b3ecba8151d28fa6f3f9a --output-root tests/fixtures/retrieval-remediation/failures

verify-retrieval-failure-fixtures: ## Regenerate Milestone 8 failure inventory in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-failure-analyse --benchmark-dir tests/fixtures/retrieval-quality/benchmark --experiment-dir tests/fixtures/retrieval-quality/experiments/RETEXP-fb2b3ecba8151d28fa6f3f9a --output-root $$tmp_dir; diff -r tests/fixtures/retrieval-remediation/failures $$tmp_dir; rm -rf $$tmp_dir

retrieval-judgment-audit: ## Audit Milestone 8 synthetic relevance judgments.
	$(PYTHON) -m healthcare_language_ai retrieval-judgment-audit --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-dir reports/retrieval-remediation/judgment-audit

retrieval-benchmark-upgrade: ## Regenerate Milestone 8 benchmark v2.1 fixture.
	$(PYTHON) -m healthcare_language_ai retrieval-benchmark-upgrade --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-dir tests/fixtures/retrieval-remediation/benchmark-v2.1

verify-retrieval-remediation-benchmark: ## Regenerate Milestone 8 benchmark v2.1 in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-benchmark-upgrade --benchmark-dir tests/fixtures/retrieval-quality/benchmark --output-dir $$tmp_dir; diff -r tests/fixtures/retrieval-remediation/benchmark-v2.1 $$tmp_dir; rm -rf $$tmp_dir

retrieval-remediation-experiment-fixtures: ## Regenerate Milestone 8 remediation experiments.
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id char_tfidf_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id word_char_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id phrase_proximity_bm25_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id field_aware_bm25_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id entity_enriched_hybrid_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id pseudo_feedback_bm25_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id multi_retriever_rrf_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id advanced_feature_reranked_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id diversified_ensemble_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id abstaining_ensemble_v1 --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root tests/fixtures/retrieval-remediation/experiments --reference-timestamp 2026-01-12T09:00:00+00:00

verify-retrieval-remediation-experiment-fixtures: ## Regenerate Milestone 8 remediation experiments in /tmp and compare.
	tmp_dir=$$(mktemp -d); for cfg in char_tfidf_v1 word_char_hybrid_v1 phrase_proximity_bm25_v1 field_aware_bm25_v1 entity_enriched_hybrid_v1 pseudo_feedback_bm25_v1 multi_retriever_rrf_v1 advanced_feature_reranked_v1 diversified_ensemble_v1 abstaining_ensemble_v1; do $(PYTHON) -m healthcare_language_ai retrieval-remediation-run --configuration-id $$cfg --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --output-root $$tmp_dir --reference-timestamp 2026-01-12T09:00:00+00:00; done; diff -r tests/fixtures/retrieval-remediation/experiments $$tmp_dir; rm -rf $$tmp_dir

retrieval-remediation-comparison-fixtures: ## Regenerate Milestone 8 remediation comparison.
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-compare --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --configuration-registry config/retrieval-remediation-configurations.yaml --output-root tests/fixtures/retrieval-remediation/comparison --reference-timestamp 2026-01-12T09:00:00+00:00

verify-retrieval-remediation-comparison-fixtures: ## Regenerate Milestone 8 remediation comparison in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai retrieval-remediation-compare --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1 --configuration-registry config/retrieval-remediation-configurations.yaml --output-root $$tmp_dir --reference-timestamp 2026-01-12T09:00:00+00:00; diff -r tests/fixtures/retrieval-remediation/comparison $$tmp_dir; rm -rf $$tmp_dir

retrieval-remediation-validate: ## Validate Milestone 8 retrieval-remediation fixtures.
	$(PYTHON) -m healthcare_language_ai retrieval-failure-validate --failure-dir tests/fixtures/retrieval-remediation/failures/RFAIL-43f65b8f8118261fe023e705
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-validate --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-validate --experiment-dir tests/fixtures/retrieval-remediation/experiments/REMEXP-41fd5fa127ab616f7f74cc9b
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-compare-validate --comparison-dir tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352

retrieval-remediation-summary: ## Summarize Milestone 8 retrieval-remediation fixtures.
	$(PYTHON) -m healthcare_language_ai retrieval-failure-summary --failure-dir tests/fixtures/retrieval-remediation/failures/RFAIL-43f65b8f8118261fe023e705
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-summary --experiment-dir tests/fixtures/retrieval-remediation/experiments/REMEXP-41fd5fa127ab616f7f74cc9b
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-compare-summary --comparison-dir tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352

retrieval-remediation-approval: ## Print Milestone 8 remediation approval decision.
	$(PYTHON) -m healthcare_language_ai retrieval-remediation-approval --comparison-dir tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352

rag-query-fixtures: ## Regenerate checked-in guarded RAG query fixtures.
	$(PYTHON) -m healthcare_language_ai rag-query-fixtures --output-dir tests/fixtures/rag/queries --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1

verify-rag-query-fixtures: ## Regenerate guarded RAG query fixtures in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai rag-query-fixtures --output-dir $$tmp_dir --benchmark-dir tests/fixtures/retrieval-remediation/benchmark-v2.1; diff -r tests/fixtures/rag/queries $$tmp_dir; rm -rf $$tmp_dir

rag-run-fixtures: ## Regenerate checked-in deterministic guarded RAG run fixture.
	$(PYTHON) -m healthcare_language_ai rag-run --query-set tests/fixtures/rag/queries/rag_queries.jsonl --retrieval-comparison-dir tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352 --output-root tests/fixtures/rag/runs --generator deterministic_extract --reference-timestamp 2026-01-16T09:00:00+00:00

verify-rag-run-fixtures: ## Regenerate guarded RAG run fixture in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai rag-run --query-set tests/fixtures/rag/queries/rag_queries.jsonl --retrieval-comparison-dir tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352 --output-root $$tmp_dir --generator deterministic_extract --reference-timestamp 2026-01-16T09:00:00+00:00; diff -r tests/fixtures/rag/runs $$tmp_dir; rm -rf $$tmp_dir

rag-evaluation-fixtures: ## Regenerate checked-in guarded RAG evaluation fixture.
	$(PYTHON) -m healthcare_language_ai rag-evaluate --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874 --expected-outcomes tests/fixtures/rag/queries/rag_expected_outcomes.jsonl --output-root tests/fixtures/rag/evaluation --reference-timestamp 2026-01-17T09:00:00+00:00

verify-rag-evaluation-fixtures: ## Regenerate guarded RAG evaluation fixture in /tmp and compare.
	tmp_dir=$$(mktemp -d); $(PYTHON) -m healthcare_language_ai rag-evaluate --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874 --expected-outcomes tests/fixtures/rag/queries/rag_expected_outcomes.jsonl --output-root $$tmp_dir --reference-timestamp 2026-01-17T09:00:00+00:00; diff -r tests/fixtures/rag/evaluation $$tmp_dir; rm -rf $$tmp_dir

rag-validate: ## Validate guarded RAG fixtures.
	$(PYTHON) -m healthcare_language_ai rag-validate --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874
	$(PYTHON) -m healthcare_language_ai rag-evaluate-validate --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017

rag-summary: ## Summarize guarded RAG fixtures.
	$(PYTHON) -m healthcare_language_ai rag-summary --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874
	$(PYTHON) -m healthcare_language_ai rag-evaluate-summary --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017

rag-approval: ## Print guarded RAG approval decision.
	$(PYTHON) -m healthcare_language_ai rag-approval --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017

rag-trace: ## Print a bounded guarded RAG trace for the first fixture query.
	$(PYTHON) -m healthcare_language_ai rag-trace --rag-dir tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874 --query-id RAGQ-52586597c68bc36f48

rag-mlflow-plan: ## Print guarded RAG MLflow dry-run plan.
	$(PYTHON) -m healthcare_language_ai rag-mlflow-plan --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017

rag-databricks-plan: ## Print guarded RAG Databricks dry-run plan.
	$(PYTHON) -m healthcare_language_ai rag-databricks-plan --evaluation-dir tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017

embedding-benchmark-local: ## Run optional local embedding benchmark; requires LOCAL_MODEL_PATH.
	test -n "$(LOCAL_MODEL_PATH)"
	$(PYTHON) -m healthcare_language_ai embedding-benchmark-run --benchmark-dir tests/fixtures/retrieval-quality/benchmark --local-model-path "$(LOCAL_MODEL_PATH)" --output-root outputs/retrieval-quality/embedding-benchmarks --reference-timestamp 2026-01-10T09:00:00+00:00

docker-build: ## Build the local Docker image.
	docker build -t healthcare-language-ai-platform:milestone-12 .

docker-run: ## Run the local Docker image.
	docker run --rm healthcare-language-ai-platform:milestone-12 healthcare-language-ai portfolio-final-summary

clean: ## Remove local Python quality caches.
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
