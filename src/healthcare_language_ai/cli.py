"""Typer command-line interface for Milestone 1 foundation tasks."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from healthcare_language_ai import __version__
from healthcare_language_ai.api.app import create_app
from healthcare_language_ai.api.schemas import (
    AnswerResponse,
    ApiError,
    ApprovalResponse,
    CitationResponse,
    EvidenceResponse,
    HealthResponse,
    MetricSummaryResponse,
    QualityGateResponse,
    QueryRequest,
    QueryResponse,
    ReadinessResponse,
    SystemStatusResponse,
    TraceResponse,
)
from healthcare_language_ai.application.contracts import DISCLAIMER
from healthcare_language_ai.application.dependencies import build_services
from healthcare_language_ai.assurance.backup import create_backup, validate_backup
from healthcare_language_ai.assurance.compatibility import compare_contracts
from healthcare_language_ai.assurance.configuration import write_configuration_assurance
from healthcare_language_ai.assurance.container import run_container_assurance
from healthcare_language_ai.assurance.contracts import (
    AssuranceGateResult,
    BackupManifest,
    CompatibilityReport,
    ComponentReadiness,
    ContainerAssuranceCheck,
    ContractBaseline,
    ContractChange,
    ContractInventoryRecord,
    DependencyInventory,
    DependencyRecord,
    MalformedEventRecord,
    OperationalEventManifest,
    PortfolioAssuranceDecision,
    RecoveryExercise,
    RestoreManifest,
    RuntimeSmokeReport,
    SbomDocument,
    SecurityControlCheck,
)
from healthcare_language_ai.assurance.dependencies import (
    write_dependency_inventory,
    write_sbom,
)
from healthcare_language_ai.assurance.inventory import write_contract_inventory
from healthcare_language_ai.assurance.recovery import restore_backup, run_recovery_exercise
from healthcare_language_ai.assurance.reports import generate_portfolio_assurance
from healthcare_language_ai.assurance.runtime import (
    run_api_smoke,
    run_dashboard_smoke,
    write_expected_smoke_fixtures,
)
from healthcare_language_ai.assurance.security import run_security_assurance
from healthcare_language_ai.config import load_settings, validate_local_environment
from healthcare_language_ai.constants import APPLICATION_NAME
from healthcare_language_ai.demonstration.contracts import DemoResult, DemoScenario, DemoSession
from healthcare_language_ai.demonstration.reports import (
    write_demo_report,
    write_portfolio_summary,
)
from healthcare_language_ai.demonstration.runner import run_demo_session
from healthcare_language_ai.demonstration.validation import validate_demo_dir
from healthcare_language_ai.domain.enums import ClinicalDocumentType
from healthcare_language_ai.embeddings.benchmarking import write_hash_embedding_benchmark
from healthcare_language_ai.embeddings.local_sentence_transformer import inspect_local_model
from healthcare_language_ai.evaluation.pipeline import load_evaluation_manifest, run_evaluation
from healthcare_language_ai.evaluation.retrieval_pipeline import (
    evaluate_retrieval,
    load_retrieval_evaluation_manifest,
)
from healthcare_language_ai.evaluation.validation import validate_evaluation_dir
from healthcare_language_ai.exceptions import HealthcareLanguageAIError
from healthcare_language_ai.extraction.pipeline import load_extraction_manifest, run_extraction
from healthcare_language_ai.extraction.validation import validate_extraction_dir
from healthcare_language_ai.ingestion.contracts import IngestionMode, OverwritePolicy
from healthcare_language_ai.ingestion.pipeline import load_ingestion_manifest, run_ingestion
from healthcare_language_ai.ingestion.quality import validate_ingestion_dir
from healthcare_language_ai.logging import configure_logging
from healthcare_language_ai.observability.contracts import (
    MetricSnapshot,
    OperationalEvent,
    OperationalSummary,
    ReadinessSnapshot,
)
from healthcare_language_ai.observability.integrity import validate_operational_integrity
from healthcare_language_ai.observability.quarantine import quarantine_summary
from healthcare_language_ai.observability.validation import validate_event_dir
from healthcare_language_ai.portfolio.contracts import (
    ArchitectureArtifact,
    CapabilityRecord,
    CleanlinessCheck,
    DocumentationCheck,
    EvidenceIndexRecord,
    MilestoneAudit,
    PortfolioModelCard,
    ReleaseGateResult,
    ReleaseManifest,
    ReleasePackageManifest,
    ReleaseReadinessReport,
    RepositoryAuditRecord,
    RepositorySizeRecord,
    RoleAlignment,
    RunRegistry,
    SuccessProfileEvidence,
    TechnologyRecord,
    TraceabilityRecord,
)
from healthcare_language_ai.portfolio.reports import (
    final_summary,
    run_cleanliness,
    run_size_audit,
    validate_documentation,
    validate_release_package,
    write_architecture_pack,
    write_capability_map,
    write_decisions,
    write_demo_pack,
    write_evidence_index,
    write_interview_pack,
    write_milestone_audit,
    write_portfolio_model_card,
    write_release_manifest,
    write_release_package,
    write_release_readiness,
    write_repository_audit,
    write_role_alignment,
    write_run_registry,
    write_static_portfolio_docs,
    write_technology_map,
    write_traceability,
)
from healthcare_language_ai.preprocessing.contracts import PreprocessingMode
from healthcare_language_ai.preprocessing.pipeline import (
    load_preprocessing_manifest,
    run_preprocessing,
)
from healthcare_language_ai.preprocessing.validation import validate_preprocessing_dir
from healthcare_language_ai.rag.contracts import RagEvaluationManifest, RagManifest
from healthcare_language_ai.rag.pipeline import (
    evaluate_rag,
    generate_rag_query_fixtures,
    run_rag,
    validate_rag_dir,
)
from healthcare_language_ai.rag.pipeline import (
    validate_evaluation_dir as validate_rag_evaluation_dir,
)
from healthcare_language_ai.retrieval.contracts import RetrievalStrategy
from healthcare_language_ai.retrieval.pipeline import (
    build_index,
    load_index_manifest,
    load_retrieval_manifest,
    run_retrieval,
)
from healthcare_language_ai.retrieval.query_fixtures import generate_query_fixture
from healthcare_language_ai.retrieval.validation import (
    validate_index_dir,
    validate_retrieval_dir,
    validate_retrieval_evaluation_dir,
)
from healthcare_language_ai.retrieval_quality.benchmark import (
    generate_benchmark,
)
from healthcare_language_ai.retrieval_quality.configurations import (
    write_default_registry,
)
from healthcare_language_ai.retrieval_quality.contracts import (
    BenchmarkManifest,
    HoldoutManifest,
    RetrievalApprovalDecision,
    RetrievalComparisonManifest,
    RetrievalExperimentManifest,
)
from healthcare_language_ai.retrieval_quality.experiments import (
    compare_configurations,
    run_experiment,
    validate_comparison_dir,
    validate_experiment_dir,
)
from healthcare_language_ai.retrieval_quality.features import expand_query_text
from healthcare_language_ai.retrieval_quality.holdout import (
    validate_holdout_dir,
    write_holdout,
)
from healthcare_language_ai.retrieval_quality.io import read_jsonl, write_jsonl
from healthcare_language_ai.retrieval_quality.review import write_review_pack
from healthcare_language_ai.retrieval_remediation.contracts import (
    BenchmarkUpgradeManifest,
    FailureAnalysisManifest,
    RemediationApprovalDecision,
    RemediationComparisonManifest,
    RemediationExperimentManifest,
)
from healthcare_language_ai.retrieval_remediation.pipeline import (
    analyse_failures,
    audit_judgments,
    compare_remediation,
    run_remediation_experiment,
    upgrade_benchmark,
    validate_failure_dir,
)
from healthcare_language_ai.retrieval_remediation.pipeline import (
    validate_benchmark_dir as validate_remediation_benchmark_dir,
)
from healthcare_language_ai.retrieval_remediation.pipeline import (
    validate_comparison_dir as validate_remediation_comparison_dir,
)
from healthcare_language_ai.retrieval_remediation.pipeline import (
    validate_experiment_dir as validate_remediation_experiment_dir,
)
from healthcare_language_ai.retrieval_remediation.registry import (
    write_default_registry as write_remediation_registry,
)
from healthcare_language_ai.synthetic.generator import generate_dataset, write_dataset
from healthcare_language_ai.synthetic.manifest import annotation_label_counts, document_type_counts
from healthcare_language_ai.synthetic.validation import (
    load_dataset,
    validate_dataset_dir,
    validation_status,
)

app = typer.Typer(
    name="healthcare-language-ai",
    help="Foundation CLI for the synthetic healthcare language AI platform.",
    no_args_is_help=True,
)

ConfigOption = Annotated[
    Path | None,
    typer.Option("--config", "-c", exists=False, help="Optional YAML configuration file."),
]


@app.command()
def version() -> None:
    """Print the application name and package version."""
    typer.echo(f"{APPLICATION_NAME} {__version__}")


@app.command("config-show")
def config_show(config: ConfigOption = None) -> None:
    """Print the effective sanitized configuration."""
    try:
        settings = load_settings(config)
    except HealthcareLanguageAIError as exc:
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(settings.sanitized(), indent=2, sort_keys=True))


@app.command("validate-environment")
def validate_environment(config: ConfigOption = None) -> None:
    """Validate local configuration and required directories."""
    try:
        settings = load_settings(config)
        configure_logging(settings)
        paths = validate_local_environment(settings)
    except HealthcareLanguageAIError as exc:
        typer.echo(f"Environment validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Environment validation passed")
    for path in paths:
        typer.echo(f"- {path}")


def _parse_document_types(
    value: str, allowed: list[ClinicalDocumentType]
) -> list[ClinicalDocumentType]:
    allowed_by_value = {document_type.value: document_type for document_type in allowed}
    if value == "all":
        return list(allowed)
    requested = [item.strip() for item in value.split(",") if item.strip()]
    if not requested:
        raise typer.BadParameter("document type selection must not be empty")
    unsupported = sorted(set(requested).difference(allowed_by_value))
    if unsupported:
        supported = ", ".join(["all", *sorted(allowed_by_value)])
        raise typer.BadParameter(
            f"unsupported document type(s): {unsupported}; supported: {supported}"
        )
    return [allowed_by_value[item] for item in requested]


def _parse_reference_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("reference timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise typer.BadParameter("reference timestamp must be timezone-aware")
    return parsed


@app.command("synthetic-generate")
def synthetic_generate(
    count: Annotated[int | None, typer.Option("--count", min=1)] = None,
    seed: Annotated[int | None, typer.Option("--seed")] = None,
    document_type: Annotated[str, typer.Option("--document-type")] = "all",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("outputs/synthetic"),
    config: ConfigOption = None,
) -> None:
    """Generate deterministic synthetic clinical-document fixtures."""
    try:
        settings = load_settings(config)
        synthetic_settings = settings.synthetic_generation
        resolved_count = count or synthetic_settings.default_record_count
        if resolved_count > synthetic_settings.maximum_records_per_run:
            maximum = synthetic_settings.maximum_records_per_run
            msg = f"count exceeds maximum_records_per_run ({maximum})"
            raise typer.BadParameter(msg)
        resolved_seed = seed if seed is not None else synthetic_settings.generator_seed
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else synthetic_settings.reference_timestamp
        )
        selected_types = _parse_document_types(
            document_type, synthetic_settings.allowed_document_types
        )
        dataset = generate_dataset(
            count=resolved_count,
            seed=resolved_seed,
            document_types=selected_types,
            reference_timestamp=resolved_timestamp,
            max_document_text_length=settings.max_document_text_length,
            generator_version=synthetic_settings.generator_version,
            template_version=synthetic_settings.template_version,
            vocabulary_version=synthetic_settings.vocabulary_version,
        )
        write_dataset(
            dataset=dataset,
            output_dir=output_dir,
            seed=resolved_seed,
            reference_timestamp=resolved_timestamp,
            generator_version=synthetic_settings.generator_version,
            template_version=synthetic_settings.template_version,
            vocabulary_version=synthetic_settings.vocabulary_version,
        )
    except (HealthcareLanguageAIError, ValueError, typer.BadParameter) as exc:
        typer.echo(f"Synthetic generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Synthetic generation completed")
    typer.echo(f"Record count: {len(dataset.records)}")
    typer.echo(f"Output directory: {output_dir}")
    status = dataset.quality_report.validation_status if dataset.quality_report else "unknown"
    typer.echo(f"Validation status: {status}")


@app.command("synthetic-validate")
def synthetic_validate(
    dataset_dir: Annotated[Path, typer.Option("--dataset-dir")] = Path("outputs/synthetic"),
    config: ConfigOption = None,
) -> None:
    """Validate an existing generated synthetic dataset."""
    try:
        settings = load_settings(config)
        checks = validate_dataset_dir(
            dataset_dir, max_document_text_length=settings.max_document_text_length
        )
    except (HealthcareLanguageAIError, ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Synthetic validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    status = validation_status(checks)
    typer.echo(f"Validation status: {status}")
    typer.echo(f"Checks: {len(checks)}")
    if status == "failed":
        for check in checks:
            if check.status == "failed":
                typer.echo(f"- {check.name}: {check.message}", err=True)
        raise typer.Exit(code=1)


@app.command("synthetic-summary")
def synthetic_summary(
    dataset_dir: Annotated[Path, typer.Option("--dataset-dir")] = Path("outputs/synthetic"),
) -> None:
    """Print a sanitized summary for a generated synthetic dataset."""
    try:
        records, manifest = load_dataset(dataset_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Synthetic summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Record count: {len(records)}")
    typer.echo(
        f"Document-type distribution: {json.dumps(document_type_counts(records), sort_keys=True)}"
    )
    annotation_counts = json.dumps(annotation_label_counts(records), sort_keys=True)
    typer.echo(f"Annotation-label distribution: {annotation_counts}")
    typer.echo(f"Seed: {manifest.seed}")
    typer.echo(f"Reference timestamp: {manifest.reference_timestamp.isoformat()}")
    typer.echo(f"Generator version: {manifest.generator_version}")
    typer.echo("Validation status: see data_quality_report.json")


def _parse_ingestion_mode(value: str) -> IngestionMode:
    try:
        return IngestionMode(value)
    except ValueError as exc:
        raise typer.BadParameter("mode must be one of: strict, quarantine") from exc


def _parse_overwrite_policy(value: str) -> OverwritePolicy:
    try:
        return OverwritePolicy(value)
    except ValueError as exc:
        raise typer.BadParameter(
            "overwrite policy must be one of: fail_if_exists, replace_identical, force_replace"
        ) from exc


def _parse_retrieval_strategy(value: str) -> RetrievalStrategy:
    try:
        return RetrievalStrategy(value)
    except ValueError as exc:
        raise typer.BadParameter("strategy must be one of: keyword, tfidf, bm25, hybrid") from exc


def _parse_k_values(value: str) -> list[int]:
    try:
        parsed = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise typer.BadParameter("k-values must be comma-separated integers") from exc
    if not parsed or any(item <= 0 for item in parsed):
        raise typer.BadParameter("k-values must contain positive integers")
    return sorted(set(parsed))


@app.command("ingest-run")
def ingest_run(
    source_dir: Annotated[Path, typer.Option("--source-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/ingestion"),
    mode: Annotated[str, typer.Option("--mode")] = "strict",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Run deterministic local ingestion for a synthetic dataset."""
    try:
        settings = load_settings(config)
        ingestion_settings = settings.ingestion
        selected_mode = _parse_ingestion_mode(mode)
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else ingestion_settings.ingestion_reference_timestamp
        )
        output_dir = run_ingestion(
            source_dir=source_dir,
            output_root=output_root,
            mode=selected_mode,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=ingestion_settings,
            max_document_text_length=settings.max_document_text_length,
        )
        manifest = load_ingestion_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Ingestion failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Ingestion completed")
    typer.echo(f"Run ID: {manifest.ingestion_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("ingest-validate")
def ingest_validate(
    ingestion_dir: Annotated[Path, typer.Option("--ingestion-dir")],
) -> None:
    """Validate persisted local ingestion evidence."""
    try:
        failures = validate_ingestion_dir(ingestion_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Ingestion validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Ingestion validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Ingestion validation passed")


@app.command("ingest-summary")
def ingest_summary(
    ingestion_dir: Annotated[Path, typer.Option("--ingestion-dir")],
) -> None:
    """Print safe ingestion metadata without clinical text."""
    try:
        manifest = load_ingestion_manifest(ingestion_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Ingestion summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Run ID: {manifest.ingestion_run_id}")
    typer.echo(f"Mode: {manifest.ingestion_mode.value}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Source dataset: {manifest.source_dataset_name}")
    typer.echo(f"Source count: {manifest.source_record_count}")
    typer.echo(f"Canonical count: {manifest.canonical_document_count}")
    typer.echo(f"Quarantine count: {manifest.quarantine_count}")
    typer.echo(
        f"Document-type distribution: {json.dumps(manifest.document_type_counts, sort_keys=True)}"
    )
    annotation_counts = json.dumps(manifest.annotation_label_counts, sort_keys=True)
    typer.echo(f"Annotation-label distribution: {annotation_counts}")
    typer.echo(f"Reconciliation status: {manifest.reconciliation_status}")
    typer.echo(f"Output path: {ingestion_dir}")


@app.command("snowflake-plan")
def snowflake_plan(
    ingestion_dir: Annotated[Path, typer.Option("--ingestion-dir")],
) -> None:
    """Validate and print a Snowflake target-state dry-run plan summary."""
    try:
        failures = validate_ingestion_dir(ingestion_dir)
        manifest = load_ingestion_manifest(ingestion_dir)
        plan_path = ingestion_dir / "snowflake_load_plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Snowflake plan validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Snowflake plan validation failed", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Target database: {plan['target_database']}")
    typer.echo(f"Target schemas: {', '.join(plan['target_schemas'])}")
    typer.echo(f"Target tables: {len(plan['target_tables'])}")
    typer.echo(f"Input files: {', '.join(plan['input_files'])}")
    typer.echo(f"Expected documents: {manifest.canonical_document_count}")
    typer.echo(f"Expected annotations: {manifest.canonical_annotation_count}")
    typer.echo(f"Required role: {plan['required_target_state_role']}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo("No Snowflake connection will be attempted.")


def _parse_preprocessing_mode(value: str) -> PreprocessingMode:
    try:
        return PreprocessingMode(value)
    except ValueError as exc:
        raise typer.BadParameter("mode must be one of: conservative, analytical") from exc


@app.command("preprocess-run")
def preprocess_run(
    ingestion_dir: Annotated[Path, typer.Option("--ingestion-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/preprocessing"),
    mode: Annotated[str, typer.Option("--mode")] = "conservative",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Run deterministic local preprocessing for canonical ingestion evidence."""
    try:
        settings = load_settings(config)
        preprocessing_settings = settings.preprocessing
        selected_mode = _parse_preprocessing_mode(mode)
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else preprocessing_settings.preprocessing_reference_timestamp
        )
        output_dir = run_preprocessing(
            ingestion_dir=ingestion_dir,
            output_root=output_root,
            mode=selected_mode,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=preprocessing_settings,
        )
        manifest = load_preprocessing_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Preprocessing failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Preprocessing completed")
    typer.echo(f"Run ID: {manifest.preprocessing_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("preprocess-validate")
def preprocess_validate(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
) -> None:
    """Validate persisted local preprocessing evidence."""
    try:
        failures = validate_preprocessing_dir(preprocessing_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Preprocessing validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Preprocessing validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Preprocessing validation passed")


@app.command("preprocess-summary")
def preprocess_summary(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
) -> None:
    """Print safe preprocessing metadata without clinical text."""
    try:
        manifest = load_preprocessing_manifest(preprocessing_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Preprocessing summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Run ID: {manifest.preprocessing_run_id}")
    typer.echo(f"Mode: {manifest.preprocessing_mode.value}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Source ingestion run ID: {manifest.source_ingestion_run_id}")
    typer.echo(f"Document count: {manifest.processed_document_count}")
    typer.echo(f"Section count: {manifest.section_count}")
    typer.echo(f"Sentence count: {manifest.sentence_count}")
    typer.echo(f"Token count: {manifest.total_lexical_token_count}")
    typer.echo(f"Projected annotation count: {manifest.projected_annotation_count}")
    typer.echo(f"Unresolved annotation count: {manifest.unresolved_annotation_count}")
    typer.echo(f"Warning count: {manifest.warning_count}")
    typer.echo(f"Failure count: {manifest.failure_count}")
    typer.echo(f"Reconciliation status: {manifest.reconciliation_status}")
    typer.echo(f"Output path: {preprocessing_dir}")


@app.command("databricks-plan")
def databricks_plan(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
) -> None:
    """Validate and print a Databricks target-state dry-run summary."""
    try:
        failures = validate_preprocessing_dir(preprocessing_dir)
        manifest = load_preprocessing_manifest(preprocessing_dir)
        plan = json.loads((preprocessing_dir / "databricks_pipeline_plan.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Databricks plan validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Databricks plan validation failed", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Medallion layers: {', '.join(plan['target_medallion_layers'])}")
    typer.echo(f"Target-state tables: {len(plan['target_table_contracts'])}")
    typer.echo(f"Notebook sequence: {len(plan['notebook_task_sequence'])}")
    typer.echo(f"Job task count: {len(plan['job_contract']['task_order'])}")
    typer.echo(f"Expected documents: {manifest.processed_document_count}")
    typer.echo(f"Expected sentences: {manifest.sentence_count}")
    typer.echo(f"Quality-gate status: {plan['quality_gates']['quality_status']}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")


@app.command("extract-run")
def extract_run(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/extraction"),
    text_representation: Annotated[str, typer.Option("--text-representation")] = "normalised_text",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Run deterministic local rule-based extraction."""
    try:
        settings = load_settings(config)
        extraction_settings = settings.extraction
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else extraction_settings.extraction_reference_timestamp
        )
        output_dir = run_extraction(
            preprocessing_dir=preprocessing_dir,
            output_root=output_root,
            text_representation=text_representation,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=extraction_settings,
        )
        manifest = load_extraction_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Extraction failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Extraction completed")
    typer.echo(f"Run ID: {manifest.extraction_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("extract-validate")
def extract_validate(
    extraction_dir: Annotated[Path, typer.Option("--extraction-dir")],
) -> None:
    """Validate persisted local extraction evidence."""
    try:
        failures = validate_extraction_dir(extraction_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Extraction validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Extraction validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Extraction validation passed")


@app.command("extract-summary")
def extract_summary(
    extraction_dir: Annotated[Path, typer.Option("--extraction-dir")],
) -> None:
    """Print safe extraction metadata without clinical text."""
    try:
        manifest = load_extraction_manifest(extraction_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Extraction summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Extraction run ID: {manifest.extraction_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Source preprocessing run ID: {manifest.source_preprocessing_run_id}")
    typer.echo(f"Document count: {manifest.source_document_count}")
    typer.echo(f"Entity prediction count: {manifest.entity_prediction_count}")
    label_counts = json.dumps(manifest.prediction_label_counts, sort_keys=True)
    typer.echo(f"Prediction counts by label: {label_counts}")
    typer.echo(
        "Document classification counts: "
        f"{json.dumps(manifest.document_type_prediction_counts, sort_keys=True)}"
    )
    typer.echo(f"Candidate count: {manifest.candidate_count}")
    typer.echo(f"Suppressed-overlap count: {manifest.suppressed_overlap_count}")
    typer.echo(f"Reconciliation status: {manifest.reconciliation_status}")
    typer.echo(f"Output path: {extraction_dir}")


@app.command("evaluate-run")
def evaluate_run(
    extraction_dir: Annotated[Path, typer.Option("--extraction-dir")],
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/evaluation"),
    matching_policy: Annotated[str, typer.Option("--matching-policy")] = "exact",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Run deterministic local baseline evaluation."""
    try:
        settings = load_settings(config)
        evaluation_settings = settings.evaluation
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else evaluation_settings.evaluation_reference_timestamp
        )
        output_dir = run_evaluation(
            extraction_dir=extraction_dir,
            preprocessing_dir=preprocessing_dir,
            output_root=output_root,
            matching_policy=matching_policy,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=evaluation_settings,
        )
        manifest = load_evaluation_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Evaluation completed")
    typer.echo(f"Run ID: {manifest.evaluation_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("evaluate-validate")
def evaluate_validate(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Validate persisted local evaluation evidence."""
    try:
        failures = validate_evaluation_dir(evaluation_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Evaluation validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Evaluation validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Evaluation validation passed")


@app.command("evaluate-summary")
def evaluate_summary(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Print safe evaluation metadata without clinical text."""
    try:
        manifest = load_evaluation_manifest(evaluation_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Evaluation summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Evaluation run ID: {manifest.evaluation_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Entity micro precision: {manifest.micro_precision}")
    typer.echo(f"Entity micro recall: {manifest.micro_recall}")
    typer.echo(f"Entity micro F1: {manifest.micro_f1}")
    typer.echo(f"Entity macro F1: {manifest.macro_f1}")
    typer.echo(f"Classification accuracy: {manifest.classification_accuracy}")
    typer.echo(f"Classification macro F1: {manifest.classification_macro_f1}")
    typer.echo(f"True positives: {manifest.true_positive_count}")
    typer.echo(f"False positives: {manifest.false_positive_count}")
    typer.echo(f"False negatives: {manifest.false_negative_count}")
    typer.echo(f"Error count: {manifest.error_count}")
    typer.echo(f"Output path: {evaluation_dir}")


@app.command("mlflow-plan")
def mlflow_plan(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Validate and print an MLflow target-state dry-run summary."""
    try:
        failures = validate_evaluation_dir(evaluation_dir)
        manifest = load_evaluation_manifest(evaluation_dir)
        plan = json.loads((evaluation_dir / "mlflow_experiment_plan.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"MLflow plan validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("MLflow plan validation failed", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Experiment placeholder: {plan['experiment_name_placeholder']}")
    typer.echo(f"Extraction run ID: {plan['extraction_run_id']}")
    typer.echo(f"Evaluation run ID: {manifest.evaluation_run_id}")
    typer.echo(f"Parameter count: {len(plan['parameters'])}")
    typer.echo(f"Metric count: {len(plan['metrics_to_log'])}")
    typer.echo(f"Artifact count: {len(plan['artifacts_to_log'])}")
    typer.echo(f"Dataset lineage status: {bool(plan['dataset_lineage'])}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")


@app.command("retrieval-query-fixtures")
def retrieval_query_fixtures(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir")],
) -> None:
    """Generate deterministic retrieval query fixtures."""
    try:
        generated = generate_query_fixture(
            preprocessing_dir=preprocessing_dir,
            output_dir=output_dir,
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval query fixture generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval query fixtures completed")
    typer.echo(f"Output directory: {generated}")


@app.command("index-build")
def index_build(
    preprocessing_dir: Annotated[Path, typer.Option("--preprocessing-dir")],
    extraction_dir: Annotated[Path, typer.Option("--extraction-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/retrieval/indexes"),
    unit_type: Annotated[str, typer.Option("--unit-type")] = "all",
    embedding_provider: Annotated[str, typer.Option("--embedding-provider")] = "deterministic_hash",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Build a local deterministic retrieval index."""
    try:
        settings = load_settings(config)
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else settings.retrieval.index_reference_timestamp
        )
        output_dir = build_index(
            preprocessing_dir=preprocessing_dir,
            extraction_dir=extraction_dir,
            output_root=output_root,
            unit_type=unit_type,
            embedding_provider=embedding_provider,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=settings.retrieval,
        )
        manifest = load_index_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Index build failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Index build completed")
    typer.echo(f"Index ID: {manifest.index_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("index-validate")
def index_validate(index_dir: Annotated[Path, typer.Option("--index-dir")]) -> None:
    """Validate persisted retrieval index evidence."""
    try:
        failures = validate_index_dir(index_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Index validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Index validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Index validation passed")


@app.command("index-summary")
def index_summary(index_dir: Annotated[Path, typer.Option("--index-dir")]) -> None:
    """Print safe retrieval index metadata."""
    try:
        manifest = load_index_manifest(index_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Index summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Index ID: {manifest.index_id}")
    typer.echo(f"Source preprocessing run ID: {manifest.source_preprocessing_run_id}")
    typer.echo(f"Unit types: {', '.join(manifest.unit_types)}")
    typer.echo(f"Retrieval-unit count: {manifest.retrieval_unit_count}")
    typer.echo(f"Vocabulary size: {manifest.vocabulary_size}")
    typer.echo(f"Embedding provider: {manifest.embedding_provider.value}")
    typer.echo(f"Embedding dimension: {manifest.embedding_dimension}")
    typer.echo(f"Available strategies: {', '.join(manifest.index_strategies)}")
    typer.echo(f"Reconciliation status: {manifest.reconciliation_status}")
    typer.echo(f"Output path: {index_dir}")


@app.command("retrieve-run")
def retrieve_run(
    index_dir: Annotated[Path, typer.Option("--index-dir")],
    query_set: Annotated[Path, typer.Option("--query-set")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/retrieval/runs"),
    strategy: Annotated[str, typer.Option("--strategy")] = "hybrid",
    top_k: Annotated[int, typer.Option("--top-k", min=1)] = 5,
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Run local deterministic retrieval."""
    try:
        settings = load_settings(config)
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        selected_strategy = _parse_retrieval_strategy(strategy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else settings.retrieval.retrieval_reference_timestamp
        )
        output_dir = run_retrieval(
            index_dir=index_dir,
            query_set=query_set,
            output_root=output_root,
            strategy=selected_strategy,
            top_k=top_k,
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=settings.retrieval,
        )
        manifest = load_retrieval_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Retrieval failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval completed")
    typer.echo(f"Run ID: {manifest.retrieval_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("retrieve-validate")
def retrieve_validate(retrieval_dir: Annotated[Path, typer.Option("--retrieval-dir")]) -> None:
    """Validate persisted retrieval run evidence."""
    try:
        failures = validate_retrieval_dir(retrieval_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Retrieval validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval validation passed")


@app.command("retrieve-summary")
def retrieve_summary(retrieval_dir: Annotated[Path, typer.Option("--retrieval-dir")]) -> None:
    """Print safe retrieval run metadata."""
    try:
        manifest = load_retrieval_manifest(retrieval_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Retrieval summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Retrieval run ID: {manifest.retrieval_run_id}")
    typer.echo(f"Index ID: {manifest.index_id}")
    typer.echo(f"Strategy: {manifest.strategy.value}")
    typer.echo(f"Query count: {manifest.query_count}")
    typer.echo(f"Top-k: {manifest.top_k}")
    typer.echo(f"Returned-result count: {manifest.returned_result_count}")
    typer.echo(f"Zero-result query count: {manifest.zero_result_query_count}")
    typer.echo(f"Filter usage: {manifest.metadata_filtered_query_count}")
    typer.echo(f"Output path: {retrieval_dir}")


@app.command("retrieval-evaluate")
def retrieval_evaluate(
    retrieval_dir: Annotated[Path, typer.Option("--retrieval-dir")],
    relevance_judgments: Annotated[Path, typer.Option("--relevance-judgments")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval/evaluation"
    ),
    k_values: Annotated[str, typer.Option("--k-values")] = "1,3,5,10",
    reference_timestamp: Annotated[str | None, typer.Option("--reference-timestamp")] = None,
    overwrite_policy: Annotated[str, typer.Option("--overwrite-policy")] = "fail_if_exists",
    config: ConfigOption = None,
) -> None:
    """Evaluate local retrieval evidence."""
    try:
        settings = load_settings(config)
        selected_policy = _parse_overwrite_policy(overwrite_policy)
        resolved_timestamp = (
            _parse_reference_timestamp(reference_timestamp)
            if reference_timestamp is not None
            else settings.retrieval.retrieval_evaluation_reference_timestamp
        )
        output_dir = evaluate_retrieval(
            retrieval_dir=retrieval_dir,
            relevance_judgments=relevance_judgments,
            output_root=output_root,
            k_values=_parse_k_values(k_values),
            reference_timestamp=resolved_timestamp,
            overwrite_policy=selected_policy,
            settings=settings.retrieval,
        )
        manifest = load_retrieval_evaluation_manifest(output_dir)
    except (HealthcareLanguageAIError, ValueError, FileExistsError, KeyError) as exc:
        typer.echo(f"Retrieval evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval evaluation completed")
    typer.echo(f"Run ID: {manifest.retrieval_evaluation_run_id}")
    typer.echo(f"Status: {manifest.run_status.value}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("retrieval-evaluate-validate")
def retrieval_evaluate_validate(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Validate persisted retrieval evaluation evidence."""
    try:
        failures = validate_retrieval_evaluation_dir(evaluation_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval evaluation validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Retrieval evaluation validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval evaluation validation passed")


@app.command("retrieval-evaluate-summary")
def retrieval_evaluate_summary(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Print safe retrieval evaluation metadata."""
    try:
        manifest = load_retrieval_evaluation_manifest(evaluation_dir)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Retrieval evaluation summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Evaluation run ID: {manifest.retrieval_evaluation_run_id}")
    typer.echo(f"Retrieval run ID: {manifest.retrieval_run_id}")
    typer.echo(f"Query count: {manifest.evaluated_query_count}")
    typer.echo(f"Hit Rate@1: {manifest.hit_rate_at_1}")
    typer.echo(f"Hit Rate@5: {manifest.hit_rate_at_5}")
    typer.echo(f"MRR: {manifest.mrr}")
    typer.echo(f"MAP: {manifest.map_score}")
    typer.echo(f"NDCG@5: {manifest.ndcg_at_5}")
    typer.echo(f"Zero-hit query count: {manifest.zero_hit_query_count}")
    typer.echo(f"Failure count: {manifest.failure_count}")
    typer.echo(f"Output path: {evaluation_dir}")


@app.command("vector-search-plan")
def vector_search_plan(evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")]) -> None:
    """Print Databricks Vector Search target-state dry-run metadata."""
    try:
        failures = validate_retrieval_evaluation_dir(evaluation_dir)
        plan = json.loads((evaluation_dir / "vector_search_plan.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Vector-search plan validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Vector-search plan validation failed", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Target-state endpoint placeholder: {plan['endpoint_placeholder']}")
    typer.echo(f"Index placeholder: {plan['index_placeholder']}")
    typer.echo(f"Primary key: {plan['primary_key']}")
    typer.echo(f"Embedding dimension: {plan['embedding_dimension']}")
    typer.echo(f"Filter columns: {', '.join(plan['metadata_filter_columns'])}")
    typer.echo(f"Source index ID: {plan['source_index_id']}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")
    typer.echo(f"Execution permitted: {str(plan['execution_permitted']).lower()}")


@app.command("retrieval-mlflow-plan")
def retrieval_mlflow_plan(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Print retrieval MLflow target-state dry-run metadata."""
    try:
        failures = validate_retrieval_evaluation_dir(evaluation_dir)
        plan = json.loads((evaluation_dir / "retrieval_mlflow_plan.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval MLflow plan validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if failures:
        typer.echo("Retrieval MLflow plan validation failed", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Experiment placeholder: {plan['experiment_name_placeholder']}")
    typer.echo(f"Index ID: {plan['index_id']}")
    typer.echo(f"Retrieval run ID: {plan['retrieval_run_id']}")
    typer.echo(f"Evaluation run ID: {plan['retrieval_evaluation_run_id']}")
    typer.echo(f"Parameter count: {len(plan['parameters'])}")
    typer.echo(f"Metric count: {len(plan['metrics'])}")
    typer.echo(f"Artifact count: {len(plan['artifacts'])}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")


@app.command("holdout-generate")
def holdout_generate(
    count: Annotated[int, typer.Option("--count", min=1)] = 40,
    seed: Annotated[int, typer.Option("--seed")] = 7026,
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "outputs/retrieval-quality/holdout"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-09T09:00:00+00:00"
    ),
) -> None:
    """Generate independent synthetic retrieval holdout evidence."""
    try:
        generated = write_holdout(
            count=count,
            seed=seed,
            output_dir=output_dir,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = HoldoutManifest.model_validate_json(
            (generated / "holdout_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Holdout generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Holdout generation completed")
    typer.echo(f"Holdout dataset ID: {manifest.holdout_dataset_id}")
    typer.echo(f"Document count: {manifest.document_count}")
    typer.echo(f"Output directory: {generated}")


@app.command("holdout-validate")
def holdout_validate(holdout_dir: Annotated[Path, typer.Option("--holdout-dir")]) -> None:
    """Validate independent retrieval holdout evidence."""
    failures = validate_holdout_dir(holdout_dir)
    if failures:
        typer.echo("Holdout validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Holdout validation passed")


@app.command("holdout-summary")
def holdout_summary(holdout_dir: Annotated[Path, typer.Option("--holdout-dir")]) -> None:
    """Print safe holdout summary."""
    try:
        manifest = HoldoutManifest.model_validate_json(
            (holdout_dir / "holdout_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Holdout summary failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Holdout dataset ID: {manifest.holdout_dataset_id}")
    typer.echo(f"Document count: {manifest.document_count}")
    typer.echo(f"Document-type counts: {json.dumps(manifest.document_type_counts, sort_keys=True)}")
    typer.echo(f"Privacy validation status: {manifest.privacy_validation_status}")
    typer.echo(f"Clinical-safety validation status: {manifest.clinical_safety_validation_status}")


@app.command("retrieval-query-expand")
def retrieval_query_expand(
    query_set: Annotated[Path, typer.Option("--query-set")],
    output_dir: Annotated[Path, typer.Option("--output-dir")],
) -> None:
    """Apply deterministic query expansion and record provenance."""
    try:
        rows = read_jsonl(query_set)
        expanded = []
        for row in rows:
            expanded_text, rules = expand_query_text(str(row["query_text"]))
            expanded.append(
                {
                    "query_id": row["query_id"],
                    "original_query_text": row["query_text"],
                    "expanded_query_text": expanded_text,
                    "applied_rules": [rule.model_dump(mode="json") for rule in rules],
                    "expansion_version": "1.0.0",
                }
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(output_dir / "expanded_queries.jsonl", expanded)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Query expansion failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Query expansion completed")
    typer.echo(f"Query count: {len(expanded)}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("retrieval-quality-query-fixtures")
def retrieval_quality_query_fixtures(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "tests/fixtures/retrieval-quality/benchmark"
    ),
    holdout_dir: Annotated[Path | None, typer.Option("--holdout-dir")] = None,
) -> None:
    """Generate expanded retrieval-quality benchmark fixtures."""
    try:
        generated = generate_benchmark(output_dir, holdout_dir=holdout_dir)
        manifest = BenchmarkManifest.model_validate_json(
            (generated / "query_set_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval-quality query fixture generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval-quality benchmark completed")
    typer.echo(f"Benchmark ID: {manifest.benchmark_id}")
    typer.echo(f"Query count: {manifest.query_count}")


@app.command("retrieval-benchmark-run")
def retrieval_benchmark_run(
    configuration_id: Annotated[str, typer.Option("--configuration-id")],
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-quality/experiments"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-10T09:00:00+00:00"
    ),
    local_model_path: Annotated[Path | None, typer.Option("--local-model-path")] = None,
) -> None:
    """Run one deterministic retrieval-quality benchmark configuration."""
    try:
        output_dir = run_experiment(
            configuration_id=configuration_id,
            benchmark_dir=benchmark_dir,
            output_root=output_root,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
            local_model_path=local_model_path,
        )
        manifest = RetrievalExperimentManifest.model_validate_json(
            (output_dir / "experiment_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval benchmark failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval benchmark completed")
    typer.echo(f"Experiment ID: {manifest.experiment_id}")
    typer.echo(f"Configuration ID: {manifest.configuration_id}")
    typer.echo(f"Validation NDCG@5: {manifest.validation_ndcg_at_5}")


@app.command("retrieval-benchmark-validate")
def retrieval_benchmark_validate(
    experiment_dir: Annotated[Path, typer.Option("--experiment-dir")],
) -> None:
    """Validate retrieval-quality experiment evidence."""
    failures = validate_experiment_dir(experiment_dir)
    if failures:
        typer.echo("Retrieval benchmark validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval benchmark validation passed")


@app.command("retrieval-benchmark-summary")
def retrieval_benchmark_summary(
    experiment_dir: Annotated[Path, typer.Option("--experiment-dir")],
) -> None:
    """Print safe retrieval-quality experiment summary."""
    manifest = RetrievalExperimentManifest.model_validate_json(
        (experiment_dir / "experiment_manifest.json").read_text()
    )
    typer.echo(f"Experiment ID: {manifest.experiment_id}")
    typer.echo(f"Configuration ID: {manifest.configuration_id}")
    typer.echo(f"Validation Hit Rate@5: {manifest.validation_hit_rate_at_5}")
    typer.echo(f"Validation NDCG@5: {manifest.validation_ndcg_at_5}")
    typer.echo(f"Quality-gate status: {manifest.quality_gate_status}")


@app.command("embedding-model-inspect")
def embedding_model_inspect(model_path: Annotated[Path, typer.Option("--model-path")]) -> None:
    """Inspect optional local embedding model metadata without downloading."""
    try:
        metadata = inspect_local_model(model_path=model_path)
    except (ValueError, FileNotFoundError) as exc:
        typer.echo(f"Embedding model inspection failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Provider: {metadata.provider_name}")
    typer.echo(f"Availability status: {metadata.availability_status}")
    typer.echo(f"Dependency available: {str(metadata.dependency_available).lower()}")
    typer.echo(f"Model checksum recorded: {bool(metadata.model_checksum)}")
    typer.echo("Automatic download attempted: false")
    typer.echo("Network connection attempted: false")


@app.command("embedding-benchmark-run")
def embedding_benchmark_run(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-quality/embedding-benchmarks"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-10T09:00:00+00:00"
    ),
    local_model_path: Annotated[Path | None, typer.Option("--local-model-path")] = None,
) -> None:
    """Write model-free hash embedding benchmark evidence by default."""
    if local_model_path is not None:
        inspect_local_model(model_path=local_model_path)
    output_dir = write_hash_embedding_benchmark(
        benchmark_dir=benchmark_dir,
        output_root=output_root,
        reference_timestamp=_parse_reference_timestamp(reference_timestamp),
    )
    typer.echo("Embedding benchmark completed")
    typer.echo(f"Output directory: {output_dir}")


@app.command("retrieval-compare")
def retrieval_compare(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    configuration_registry: Annotated[Path | None, typer.Option("--configuration-registry")] = None,
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-quality/comparison"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-11T09:00:00+00:00"
    ),
) -> None:
    """Compare model-free retrieval configurations and select a baseline."""
    try:
        if configuration_registry is not None and not configuration_registry.exists():
            write_default_registry(configuration_registry)
        output_dir = compare_configurations(
            benchmark_dir=benchmark_dir,
            configuration_registry=configuration_registry,
            output_root=output_root,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = RetrievalComparisonManifest.model_validate_json(
            (output_dir / "comparison_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval comparison failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval comparison completed")
    typer.echo(f"Comparison ID: {manifest.comparison_id}")
    typer.echo(f"Selected configuration: {manifest.selected_configuration_id}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("retrieval-compare-validate")
def retrieval_compare_validate(
    comparison_dir: Annotated[Path, typer.Option("--comparison-dir")],
) -> None:
    """Validate retrieval comparison evidence."""
    failures = validate_comparison_dir(comparison_dir)
    if failures:
        typer.echo("Retrieval comparison validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval comparison validation passed")


@app.command("retrieval-compare-summary")
def retrieval_compare_summary(
    comparison_dir: Annotated[Path, typer.Option("--comparison-dir")],
) -> None:
    """Print safe retrieval comparison summary."""
    manifest = RetrievalComparisonManifest.model_validate_json(
        (comparison_dir / "comparison_manifest.json").read_text()
    )
    typer.echo(f"Comparison ID: {manifest.comparison_id}")
    typer.echo(f"Configurations evaluated: {len(manifest.configurations_evaluated)}")
    typer.echo(f"Configurations skipped: {len(manifest.configurations_skipped)}")
    typer.echo(f"Selected configuration: {manifest.selected_configuration_id}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("retrieval-approval")
def retrieval_approval(comparison_dir: Annotated[Path, typer.Option("--comparison-dir")]) -> None:
    """Print retrieval approval decision for future RAG prototype planning."""
    decision = RetrievalApprovalDecision.model_validate_json(
        (comparison_dir / "retrieval_approval_decision.json").read_text()
    )
    typer.echo(f"Selected configuration: {decision.selected_configuration_id}")
    typer.echo(f"Approval status: {decision.approval_status}")
    approved = str(decision.approved_for_future_rag_prototype).lower()
    typer.echo(f"Approved for future RAG prototype: {approved}")
    typer.echo(f"Required gates: {decision.required_gate_count}")
    typer.echo(f"Passed required gates: {decision.passed_required_gates}")
    typer.echo(f"Failed required gates: {decision.failed_required_gates}")


@app.command("retrieval-review-pack")
def retrieval_review_pack(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/retrieval-review"),
) -> None:
    """Generate deterministic synthetic relevance-review pack."""
    try:
        generated = write_review_pack(benchmark_dir=benchmark_dir, output_dir=output_dir)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Review-pack generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval review pack completed")
    typer.echo(f"Output directory: {generated}")


@app.command("retrieval-failure-analyse")
def retrieval_failure_analyse(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    experiment_dir: Annotated[Path, typer.Option("--experiment-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-remediation/failures"
    ),
) -> None:
    """Analyze Milestone 7 retrieval failures for remediation planning."""
    try:
        output_dir = analyse_failures(
            benchmark_dir=benchmark_dir,
            experiment_dir=experiment_dir,
            output_root=output_root,
        )
        manifest = FailureAnalysisManifest.model_validate_json(
            (output_dir / "failure_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval failure analysis failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval failure analysis completed")
    typer.echo(f"Failure run ID: {manifest.failure_run_id}")
    typer.echo(f"Source experiment ID: {manifest.source_experiment_id}")
    typer.echo(f"Zero-hit count: {manifest.zero_hit_count}")


@app.command("retrieval-failure-validate")
def retrieval_failure_validate(
    failure_dir: Annotated[Path, typer.Option("--failure-dir")],
) -> None:
    """Validate retrieval-remediation failure evidence."""
    failures = validate_failure_dir(failure_dir)
    if failures:
        typer.echo("Retrieval failure validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval failure validation passed")


@app.command("retrieval-failure-summary")
def retrieval_failure_summary(failure_dir: Annotated[Path, typer.Option("--failure-dir")]) -> None:
    """Print safe retrieval failure summary."""
    manifest = FailureAnalysisManifest.model_validate_json(
        (failure_dir / "failure_manifest.json").read_text()
    )
    typer.echo(f"Failure run ID: {manifest.failure_run_id}")
    typer.echo(f"Query count: {manifest.query_count}")
    typer.echo(f"Successful query count: {manifest.successful_query_count}")
    typer.echo(f"Zero-hit count: {manifest.zero_hit_count}")
    typer.echo(
        f"Highest-priority failure cohorts: {', '.join(manifest.highest_priority_failure_cohorts)}"
    )


@app.command("retrieval-judgment-audit")
def retrieval_judgment_audit(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "outputs/retrieval-remediation/judgment-audit"
    ),
) -> None:
    """Audit synthetic retrieval judgments before remediation benchmark upgrade."""
    generated = audit_judgments(benchmark_dir=benchmark_dir, output_dir=output_dir)
    typer.echo("Retrieval judgment audit completed")
    typer.echo(f"Output directory: {generated}")


@app.command("retrieval-judgment-adjudicate")
def retrieval_judgment_adjudicate(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "outputs/retrieval-remediation/benchmark-v2.1"
    ),
) -> None:
    """Apply deterministic synthetic adjudication decisions."""
    generated = upgrade_benchmark(benchmark_dir=benchmark_dir, output_dir=output_dir)
    manifest = BenchmarkUpgradeManifest.model_validate_json(
        (generated / "query_set_manifest.json").read_text()
    )
    typer.echo("Retrieval judgment adjudication completed")
    typer.echo(f"Accepted adjudications: {manifest.accepted_adjudication_count}")
    typer.echo(f"Rejected adjudications: {manifest.rejected_adjudication_count}")


@app.command("retrieval-benchmark-upgrade")
def retrieval_benchmark_upgrade(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "outputs/retrieval-remediation/benchmark-v2.1"
    ),
) -> None:
    """Create non-mutating remediation benchmark v2.1."""
    try:
        generated = upgrade_benchmark(benchmark_dir=benchmark_dir, output_dir=output_dir)
        manifest = BenchmarkUpgradeManifest.model_validate_json(
            (generated / "query_set_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval benchmark upgrade failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval benchmark upgrade completed")
    typer.echo(f"Benchmark ID: {manifest.benchmark_id}")
    typer.echo(f"Benchmark version: {manifest.benchmark_version}")
    typer.echo(f"Query count: {manifest.query_count}")


@app.command("retrieval-remediation-run")
def retrieval_remediation_run(
    configuration_id: Annotated[str, typer.Option("--configuration-id")],
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-remediation/experiments"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-12T09:00:00+00:00"
    ),
) -> None:
    """Run one Milestone 8 remediation configuration."""
    try:
        output_dir = run_remediation_experiment(
            configuration_id=configuration_id,
            benchmark_dir=benchmark_dir,
            output_root=output_root,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = RemediationExperimentManifest.model_validate_json(
            (output_dir / "experiment_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval remediation run failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval remediation run completed")
    typer.echo(f"Experiment ID: {manifest.experiment_id}")
    typer.echo(f"Configuration ID: {manifest.configuration_id}")
    typer.echo(f"Quality-gate status: {manifest.quality_gate_status}")


@app.command("retrieval-remediation-validate")
def retrieval_remediation_validate(
    experiment_dir: Annotated[Path | None, typer.Option("--experiment-dir")] = None,
    benchmark_dir: Annotated[Path | None, typer.Option("--benchmark-dir")] = None,
) -> None:
    """Validate remediation benchmark or experiment evidence."""
    if benchmark_dir is None and experiment_dir is None:
        raise typer.BadParameter("provide --benchmark-dir or --experiment-dir")
    failures = (
        validate_remediation_benchmark_dir(benchmark_dir)
        if benchmark_dir is not None
        else validate_remediation_experiment_dir(experiment_dir)  # type: ignore[arg-type]
    )
    if failures:
        typer.echo("Retrieval remediation validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval remediation validation passed")


@app.command("retrieval-remediation-summary")
def retrieval_remediation_summary(
    experiment_dir: Annotated[Path, typer.Option("--experiment-dir")],
) -> None:
    """Print safe remediation experiment summary."""
    manifest = RemediationExperimentManifest.model_validate_json(
        (experiment_dir / "experiment_manifest.json").read_text()
    )
    typer.echo(f"Experiment ID: {manifest.experiment_id}")
    typer.echo(f"Configuration ID: {manifest.configuration_id}")
    typer.echo(f"Validation Hit@5: {manifest.validation_hit_rate_at_5}")
    typer.echo(f"Validation NDCG@5: {manifest.validation_ndcg_at_5}")
    typer.echo(f"Quality-gate status: {manifest.quality_gate_status}")


@app.command("retrieval-remediation-compare")
def retrieval_remediation_compare(
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")],
    configuration_registry: Annotated[Path | None, typer.Option("--configuration-registry")] = None,
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/retrieval-remediation/comparison"
    ),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-12T09:00:00+00:00"
    ),
) -> None:
    """Compare remediation configurations and select a RAG-prototype candidate."""
    try:
        if configuration_registry is not None and not configuration_registry.exists():
            write_remediation_registry(configuration_registry)
        output_dir = compare_remediation(
            benchmark_dir=benchmark_dir,
            configuration_registry=configuration_registry,
            output_root=output_root,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = RemediationComparisonManifest.model_validate_json(
            (output_dir / "comparison_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"Retrieval remediation comparison failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Retrieval remediation comparison completed")
    typer.echo(f"Comparison ID: {manifest.comparison_id}")
    typer.echo(f"Selected configuration: {manifest.selected_configuration_id}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("retrieval-remediation-compare-validate")
def retrieval_remediation_compare_validate(
    comparison_dir: Annotated[Path, typer.Option("--comparison-dir")],
) -> None:
    """Validate remediation comparison evidence."""
    failures = validate_remediation_comparison_dir(comparison_dir)
    if failures:
        typer.echo("Retrieval remediation comparison validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Retrieval remediation comparison validation passed")


@app.command("retrieval-remediation-compare-summary")
def retrieval_remediation_compare_summary(
    comparison_dir: Annotated[Path, typer.Option("--comparison-dir")],
) -> None:
    """Print safe remediation comparison summary."""
    manifest = RemediationComparisonManifest.model_validate_json(
        (comparison_dir / "comparison_manifest.json").read_text()
    )
    typer.echo(f"Comparison ID: {manifest.comparison_id}")
    typer.echo(f"Configs evaluated: {len(manifest.configurations_evaluated)}")
    typer.echo(f"Selected config: {manifest.selected_configuration_id}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("retrieval-remediation-approval")
def retrieval_remediation_approval(
    comparison_dir: Annotated[Path, typer.Option("--comparison-dir")],
) -> None:
    """Print remediation approval decision."""
    decision = RemediationApprovalDecision.model_validate_json(
        (comparison_dir / "retrieval_approval_decision.json").read_text()
    )
    typer.echo(f"Selected configuration: {decision.selected_configuration_id}")
    typer.echo(f"Approval status: {decision.approval_status}")
    approved = str(decision.approved_for_future_rag_prototype).lower()
    typer.echo(f"Approved for future RAG prototype: {approved}")
    typer.echo(f"Required gates: {decision.required_gate_count}")
    typer.echo(f"Passed required gates: {decision.passed_required_gates}")
    typer.echo(f"Failed required gates: {decision.failed_required_gates}")


@app.command("retrieval-abstention-summary")
def retrieval_abstention_summary(
    experiment_dir: Annotated[Path, typer.Option("--experiment-dir")],
) -> None:
    """Print abstention metrics for a remediation experiment."""
    manifest = RemediationExperimentManifest.model_validate_json(
        (experiment_dir / "experiment_manifest.json").read_text()
    )
    typer.echo(f"Configuration ID: {manifest.configuration_id}")
    typer.echo(f"Abstention enabled: {str(manifest.abstention).lower()}")
    typer.echo(f"Unanswerable abstention accuracy: {manifest.unanswerable_abstention_accuracy}")
    typer.echo(f"Answerable coverage: {manifest.answerable_coverage}")


@app.command("rag-query-fixtures")
def rag_query_fixtures(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("tests/fixtures/rag/queries"),
    benchmark_dir: Annotated[Path, typer.Option("--benchmark-dir")] = Path(
        "tests/fixtures/retrieval-remediation/benchmark-v2.1"
    ),
) -> None:
    """Generate deterministic guarded-RAG query fixtures."""
    try:
        generated = generate_rag_query_fixtures(benchmark_dir=benchmark_dir, output_dir=output_dir)
        manifest = json.loads((generated / "rag_query_manifest.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"RAG query fixture generation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("RAG query fixtures completed")
    typer.echo(f"Query count: {manifest['query_count']}")
    typer.echo(f"Output directory: {generated}")


@app.command("rag-run")
def rag_run(
    query_set: Annotated[Path, typer.Option("--query-set")],
    retrieval_comparison_dir: Annotated[Path, typer.Option("--retrieval-comparison-dir")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/rag/runs"),
    generator: Annotated[str, typer.Option("--generator")] = "deterministic_extract",
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-16T09:00:00+00:00"
    ),
) -> None:
    """Run guarded synthetic RAG with deterministic generation."""
    try:
        output_dir = run_rag(
            query_set=query_set,
            retrieval_comparison_dir=retrieval_comparison_dir,
            output_root=output_root,
            generator=generator,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = RagManifest.model_validate_json((output_dir / "rag_manifest.json").read_text())
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"RAG run failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("RAG run completed")
    typer.echo(f"RAG run ID: {manifest.rag_run_id}")
    typer.echo(f"Generator: {manifest.generator_provider}")
    typer.echo(f"Query count: {manifest.query_count}")


@app.command("rag-validate")
def rag_validate(rag_dir: Annotated[Path, typer.Option("--rag-dir")]) -> None:
    """Validate guarded RAG run evidence."""
    failures = validate_rag_dir(rag_dir)
    if failures:
        typer.echo("RAG validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("RAG validation passed")


@app.command("rag-summary")
def rag_summary(rag_dir: Annotated[Path, typer.Option("--rag-dir")]) -> None:
    """Print safe guarded-RAG run metadata."""
    manifest = RagManifest.model_validate_json((rag_dir / "rag_manifest.json").read_text())
    typer.echo(f"RAG run ID: {manifest.rag_run_id}")
    typer.echo(f"Generator: {manifest.generator_provider}")
    typer.echo(f"Query count: {manifest.query_count}")
    typer.echo(f"Grounded answer count: {manifest.grounded_answer_count}")
    typer.echo(f"Partial answer count: {manifest.partial_answer_count}")
    typer.echo(f"Refusal count: {manifest.refusal_count}")
    typer.echo(f"Retrieval-abstention count: {manifest.retrieval_abstention_count}")
    typer.echo(f"Citation failure count: {manifest.citation_validation_failure_count}")
    typer.echo(f"Groundedness failure count: {manifest.groundedness_failure_count}")
    typer.echo(f"Safety failure count: {manifest.safety_validation_failure_count}")
    typer.echo(f"Output path: {rag_dir}")


@app.command("rag-evaluate")
def rag_evaluate(
    rag_dir: Annotated[Path, typer.Option("--rag-dir")],
    expected_outcomes: Annotated[Path, typer.Option("--expected-outcomes")],
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/rag/evaluation"),
    reference_timestamp: Annotated[str, typer.Option("--reference-timestamp")] = (
        "2026-01-17T09:00:00+00:00"
    ),
) -> None:
    """Evaluate guarded synthetic RAG evidence."""
    try:
        output_dir = evaluate_rag(
            rag_dir=rag_dir,
            expected_outcomes=expected_outcomes,
            output_root=output_root,
            reference_timestamp=_parse_reference_timestamp(reference_timestamp),
        )
        manifest = RagEvaluationManifest.model_validate_json(
            (output_dir / "rag_evaluation_manifest.json").read_text()
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        typer.echo(f"RAG evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("RAG evaluation completed")
    typer.echo(f"RAG evaluation ID: {manifest.rag_evaluation_id}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("rag-evaluate-validate")
def rag_evaluate_validate(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Validate guarded-RAG evaluation evidence."""
    failures = validate_rag_evaluation_dir(evaluation_dir)
    if failures:
        typer.echo("RAG evaluation validation failed", err=True)
        for failure in failures:
            typer.echo(f"- {failure}", err=True)
        raise typer.Exit(code=1)
    typer.echo("RAG evaluation validation passed")


@app.command("rag-evaluate-summary")
def rag_evaluate_summary(
    evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")],
) -> None:
    """Print safe guarded-RAG evaluation summary."""
    manifest = RagEvaluationManifest.model_validate_json(
        (evaluation_dir / "rag_evaluation_manifest.json").read_text()
    )
    typer.echo(f"RAG evaluation ID: {manifest.rag_evaluation_id}")
    typer.echo(f"Source RAG run ID: {manifest.source_rag_run_id}")
    typer.echo(f"Answer-status accuracy: {manifest.answer_status_accuracy}")
    typer.echo(f"Citation validity rate: {manifest.citation_validity_rate}")
    typer.echo(f"Approval status: {manifest.approval_status}")


@app.command("rag-approval")
def rag_approval(evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")]) -> None:
    """Print guarded-RAG approval decision."""
    manifest = RagEvaluationManifest.model_validate_json(
        (evaluation_dir / "rag_evaluation_manifest.json").read_text()
    )
    typer.echo("RAG configuration: abstaining_ensemble_v1")
    typer.echo("Generator provider: deterministic_extract")
    typer.echo(f"Answer-status accuracy: {manifest.answer_status_accuracy}")
    typer.echo(f"Citation validity: {manifest.citation_validity_rate}")
    typer.echo(f"Citation completeness: {manifest.citation_completeness}")
    typer.echo(f"Unsupported claim rate: {manifest.unsupported_claim_rate}")
    typer.echo(f"Quality gates: {manifest.passed_required_gates}/{manifest.required_gate_count}")
    typer.echo(f"Approval status: {manifest.approval_status}")
    approved = str(manifest.approved_for_local_synthetic_demo).lower()
    typer.echo(f"Approved for local synthetic demo: {approved}")


@app.command("rag-trace")
def rag_trace(
    rag_dir: Annotated[Path, typer.Option("--rag-dir")],
    query_id: Annotated[str | None, typer.Option("--query-id")] = None,
    answer_id: Annotated[str | None, typer.Option("--answer-id")] = None,
) -> None:
    """Print bounded retrieval-to-answer trace metadata."""
    answers = read_jsonl(rag_dir / "rag_answers.jsonl")
    bundles = {row["query_id"]: row for row in read_jsonl(rag_dir / "evidence_bundles.jsonl")}
    selected = None
    for answer in answers:
        if (query_id and answer["query_id"] == query_id) or (
            answer_id and answer["answer_id"] == answer_id
        ):
            selected = answer
            break
    if selected is None:
        typer.echo("Trace target not found", err=True)
        raise typer.Exit(code=1)
    bundle = bundles[selected["query_id"]]
    typer.echo(f"Query ID: {selected['query_id']}")
    typer.echo(f"Retrieval status: {selected['retrieval_status']}")
    typer.echo(f"Retrieval confidence: {selected['retrieval_confidence']}")
    typer.echo(
        "Selected evidence IDs: "
        + ",".join(unit["evidence_id"] for unit in bundle["evidence_units"])
    )
    typer.echo(f"Prompt contract: {selected['prompt_id']}@{selected['prompt_version']}")
    typer.echo(f"Generator: {selected['generator_provider']}")
    typer.echo(f"Answer status: {selected['answer_status']}")
    typer.echo("Claim IDs: " + ",".join(claim["claim_id"] for claim in selected["claims"]))
    typer.echo(
        "Citation IDs: " + ",".join(citation["citation_id"] for citation in selected["citations"])
    )


@app.command("rag-mlflow-plan")
def rag_mlflow_plan(evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")]) -> None:
    """Print RAG MLflow dry-run plan metadata."""
    plan = json.loads((evaluation_dir / "mlflow_rag_plan.json").read_text())
    typer.echo(f"RAG run ID: {plan['rag_run_id']}")
    typer.echo(f"RAG evaluation ID: {plan['rag_evaluation_id']}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")


@app.command("rag-databricks-plan")
def rag_databricks_plan(evaluation_dir: Annotated[Path, typer.Option("--evaluation-dir")]) -> None:
    """Print RAG Databricks target-state plan metadata."""
    plan = json.loads((evaluation_dir / "databricks_rag_plan.json").read_text())
    typer.echo(f"RAG run ID: {plan['rag_run_id']}")
    typer.echo(f"Logical tables: {len(plan['logical_tables'])}")
    typer.echo(f"Dry-run status: {plan['dry_run_status']}")
    typer.echo(f"Connection attempted: {str(plan['connection_attempted']).lower()}")


@app.command("api-run")
def api_run(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8000,
    reload: Annotated[bool, typer.Option("--reload")] = False,
) -> None:
    """Run the local read-only FastAPI demonstration service."""
    if host == "0.0.0.0":
        typer.echo("Binding to 0.0.0.0 is intended only for explicit local Docker port mapping.")
    import uvicorn

    uvicorn.run("healthcare_language_ai.api.app:app", host=host, port=port, reload=reload)


@app.command("api-validate")
def api_validate() -> None:
    """Validate API imports, routes, OpenAPI generation, and readiness."""
    services = build_services()
    app_instance = create_app()
    paths = set(app_instance.openapi()["paths"])
    required = {
        "/health/live",
        "/health/ready",
        "/api/v1/system",
        "/api/v1/approvals/retrieval",
        "/api/v1/approvals/rag",
        "/api/v1/quality-gates/retrieval",
        "/api/v1/quality-gates/rag",
        "/api/v1/query",
        "/api/v1/answers/{answer_id}",
        "/api/v1/traces/{answer_id}",
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/citations/{citation_id}",
        "/api/v1/metrics/summary",
        "/api/v1/metrics/retrieval",
        "/api/v1/metrics/rag",
    }
    missing = sorted(required.difference(paths))
    readiness = services.health.ready()
    if missing or readiness.status != "ready" or services.settings.milestone10.cors_enabled:
        for item in missing:
            typer.echo(f"Missing route: {item}", err=True)
        if readiness.status != "ready":
            typer.echo("Readiness validation failed", err=True)
        if services.settings.milestone10.cors_enabled:
            typer.echo("Unsafe wildcard CORS is not permitted", err=True)
        raise typer.Exit(code=1)
    typer.echo("API validation passed")
    typer.echo(f"Routes: {len(paths)}")
    typer.echo(f"Readiness: {readiness.status}")


@app.command("api-routes")
def api_routes() -> None:
    """Print registered local API routes and read-only status."""
    app_instance = create_app()
    for route in app_instance.routes:
        path = getattr(route, "path", "")
        methods = ",".join(sorted(getattr(route, "methods", [])))
        if not path:
            continue
        read_only = (
            "true" if methods in {"GET", "HEAD", "GET,HEAD"} or path == "/api/v1/query" else "false"
        )
        synthetic_only = "true"
        typer.echo(f"{methods}\t{path}\tlocal synthetic demo route\t{read_only}\t{synthetic_only}")


@app.command("dashboard-run")
def dashboard_run(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8501,
    service_mode: Annotated[str, typer.Option("--service-mode")] = "direct",
) -> None:
    """Run the local Streamlit portfolio dashboard."""
    import subprocess

    command = [
        "streamlit",
        "run",
        "dashboard/Home.py",
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--",
        "--service-mode",
        service_mode,
    ]
    raise typer.Exit(code=subprocess.call(command))


@app.command("dashboard-validate")
def dashboard_validate() -> None:
    """Validate Streamlit page imports and shared service availability."""
    services = build_services()
    banner = DISCLAIMER
    pages = [
        Path("dashboard/Home.py"),
        Path("dashboard/pages/1_Synthetic_Query.py"),
        Path("dashboard/pages/2_RAG_Trace.py"),
        Path("dashboard/pages/3_Citation_Browser.py"),
        Path("dashboard/pages/4_Retrieval_Quality.py"),
        Path("dashboard/pages/5_RAG_Quality.py"),
        Path("dashboard/pages/6_Approvals.py"),
        Path("dashboard/pages/7_Architecture.py"),
        Path("dashboard/pages/8_Safety_and_Limitations.py"),
    ]
    missing = [str(page) for page in pages if not page.exists()]
    if missing or services.approval.rag_approval().approval_status != "approved_for_local_demo":
        for page in missing:
            typer.echo(f"Missing dashboard page: {page}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Dashboard validation passed")
    typer.echo(banner)


@app.command("system-status")
def system_status() -> None:
    """Print safe local system metadata."""
    status = build_services().health.system_status()
    for key, value in status.model_dump(mode="json").items():
        typer.echo(f"{key}: {value}")


@app.command("system-readiness")
def system_readiness() -> None:
    """Print readiness checks and return non-zero on required failure."""
    readiness = build_services().health.ready()
    typer.echo(f"status: {readiness.status}")
    for check in readiness.checks:
        typer.echo(f"{check.name}: {check.status} ({check.detail})")
    if readiness.status != "ready":
        raise typer.Exit(code=1)


@app.command("operational-summary")
def operational_summary(
    events_dir: Annotated[Path | None, typer.Option("--events-dir")] = None,
) -> None:
    """Print safe local operational metric summary."""
    services = build_services()
    if events_dir is not None:
        services.metrics.event_store.root = events_dir
    summary = services.metrics.summary()
    for key, value in summary.model_dump().items():
        typer.echo(f"{key}: {value}")


@app.command("operational-events-validate")
def operational_events_validate(
    events_dir: Annotated[Path, typer.Option("--events-dir")] = Path(
        "outputs/observability/events"
    ),
) -> None:
    """Validate safe local operational JSONL evidence."""
    failures = validate_event_dir(events_dir)
    if failures:
        for failure in failures:
            typer.echo(failure, err=True)
        raise typer.Exit(code=1)
    typer.echo("Operational events validation passed")


@app.command("demo-run")
def demo_run(
    scenario_set: Annotated[str, typer.Option("--scenario-set")] = "standard",
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/demo"),
) -> None:
    """Run deterministic fixture-backed demonstration scenarios."""
    session = run_demo_session(scenario_set=scenario_set)
    write_demo_report(session, output_dir)
    typer.echo(f"Demo session ID: {session.demo_session_id}")
    typer.echo(f"Scenario count: {session.scenario_count}")
    typer.echo(f"Passed scenarios: {session.passed_scenarios}")
    typer.echo(f"Output path: {output_dir}")


@app.command("demo-validate")
def demo_validate(
    demo_dir: Annotated[Path, typer.Option("--demo-dir")] = Path("reports/demo"),
) -> None:
    """Validate generated deterministic demo evidence."""
    failures = validate_demo_dir(demo_dir)
    if failures:
        for failure in failures:
            typer.echo(failure, err=True)
        raise typer.Exit(code=1)
    typer.echo("Demo validation passed")


@app.command("demo-summary")
def demo_summary(
    demo_dir: Annotated[Path, typer.Option("--demo-dir")] = Path("reports/demo"),
) -> None:
    """Print deterministic demo-session summary."""
    session = json.loads((demo_dir / "demo-session.json").read_text())
    typer.echo(f"Session ID: {session['demo_session_id']}")
    typer.echo(f"Scenario count: {session['scenario_count']}")
    typer.echo(f"Passed scenarios: {session['passed_scenarios']}")
    typer.echo(f"Failed scenarios: {session['failed_scenarios']}")
    typer.echo(f"Output path: {demo_dir}")


@app.command("portfolio-summary")
def portfolio_summary(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate a portfolio evidence summary from manifests."""
    path = write_portfolio_summary(output_dir)
    typer.echo(f"Portfolio summary written: {path}")


@app.command("api-contract-fixtures")
def api_contract_fixtures(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("tests/fixtures/api"),
) -> None:
    """Generate deterministic API contract fixtures."""
    services = build_services()
    output_dir.mkdir(parents=True, exist_ok=True)
    app_instance = create_app()
    (output_dir / "openapi.json").write_text(
        json.dumps(app_instance.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    routes = [
        {"path": getattr(route, "path", ""), "methods": sorted(getattr(route, "methods", []))}
        for route in app_instance.routes
        if getattr(route, "path", "")
    ]
    (output_dir / "routes.json").write_text(json.dumps(routes, indent=2, sort_keys=True) + "\n")
    first = services.evidence.queries[0]
    request = QueryRequest(query_text=str(first["query_text"]), query_id=str(first["query_id"]))
    response = services.query.run_synthetic_query(request)
    refusal = services.query.run_synthetic_query(
        QueryRequest(query_text="Give treatment advice for chest pain", portfolio_demo_mode=True)
    )
    response = response.model_copy(update={"request_id": "REQ-fixture-grounded"})
    refusal = refusal.model_copy(
        update={
            "request_id": "REQ-fixture-refusal",
            "answer_id": "REF-fixture-refusal",
            "trace_id": "REQ-fixture-refusal",
        }
    )
    (output_dir / "example-query-request.json").write_text(
        request.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "example-grounded-response.json").write_text(
        response.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "example-refusal-response.json").write_text(
        refusal.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "example-trace-response.json").write_text(
        services.trace.get_trace(response.answer_id).model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    readiness = services.health.ready().model_dump(mode="json")
    readiness["timestamp"] = "2026-01-18T09:00:00Z"
    (output_dir / "example-readiness-response.json").write_text(
        json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# API Contract Fixtures\n\nDeterministic local synthetic-only API fixtures.\n",
        encoding="utf-8",
    )
    typer.echo(f"API contract fixtures written: {output_dir}")


@app.command("schemas-generate")
def schemas_generate() -> None:
    """Generate JSON Schemas for M10 typed contracts."""
    schema_map: dict[Path, type[BaseModel]] = {
        Path("schemas/api/query-request.schema.json"): QueryRequest,
        Path("schemas/api/query-response.schema.json"): QueryResponse,
        Path("schemas/api/evidence-response.schema.json"): EvidenceResponse,
        Path("schemas/api/citation-response.schema.json"): CitationResponse,
        Path("schemas/api/metric-summary-response.schema.json"): MetricSummaryResponse,
        Path("schemas/api/health-response.schema.json"): HealthResponse,
        Path("schemas/api/readiness-response.schema.json"): ReadinessResponse,
        Path("schemas/api/api-error.schema.json"): ApiError,
        Path("schemas/application/system-status.schema.json"): SystemStatusResponse,
        Path("schemas/application/approval-response.schema.json"): ApprovalResponse,
        Path("schemas/application/quality-gate-response.schema.json"): QualityGateResponse,
        Path("schemas/application/trace-response.schema.json"): TraceResponse,
        Path("schemas/api/answer-response.schema.json"): AnswerResponse,
        Path("schemas/observability/operational-event.schema.json"): OperationalEvent,
        Path("schemas/observability/readiness-snapshot.schema.json"): ReadinessSnapshot,
        Path("schemas/observability/metric-snapshot.schema.json"): MetricSnapshot,
        Path("schemas/observability/operational-summary.schema.json"): OperationalSummary,
        Path("schemas/demonstration/demo-scenario.schema.json"): DemoScenario,
        Path("schemas/demonstration/demo-result.schema.json"): DemoResult,
        Path("schemas/demonstration/demo-session.schema.json"): DemoSession,
        Path("schemas/demonstration/portfolio-summary.schema.json"): SystemStatusResponse,
        Path("schemas/assurance/contract-inventory-record.schema.json"): ContractInventoryRecord,
        Path("schemas/assurance/contract-baseline.schema.json"): ContractBaseline,
        Path("schemas/assurance/contract-change.schema.json"): ContractChange,
        Path("schemas/assurance/compatibility-report.schema.json"): CompatibilityReport,
        Path("schemas/assurance/component-readiness.schema.json"): ComponentReadiness,
        Path("schemas/assurance/runtime-smoke-report.schema.json"): RuntimeSmokeReport,
        Path("schemas/assurance/operational-event-manifest.schema.json"): OperationalEventManifest,
        Path("schemas/assurance/malformed-event-record.schema.json"): MalformedEventRecord,
        Path("schemas/assurance/backup-manifest.schema.json"): BackupManifest,
        Path("schemas/assurance/restore-manifest.schema.json"): RestoreManifest,
        Path("schemas/assurance/recovery-exercise.schema.json"): RecoveryExercise,
        Path("schemas/assurance/security-control-check.schema.json"): SecurityControlCheck,
        Path("schemas/assurance/dependency-record.schema.json"): DependencyRecord,
        Path("schemas/assurance/dependency-inventory.schema.json"): DependencyInventory,
        Path("schemas/assurance/sbom.schema.json"): SbomDocument,
        Path("schemas/assurance/container-assurance.schema.json"): ContainerAssuranceCheck,
        Path("schemas/assurance/assurance-gate-result.schema.json"): AssuranceGateResult,
        Path(
            "schemas/assurance/portfolio-assurance-decision.schema.json"
        ): PortfolioAssuranceDecision,
        Path("schemas/portfolio/repository-audit-record.schema.json"): RepositoryAuditRecord,
        Path("schemas/portfolio/milestone-audit.schema.json"): MilestoneAudit,
        Path("schemas/portfolio/traceability-record.schema.json"): TraceabilityRecord,
        Path("schemas/portfolio/architecture-artifact.schema.json"): ArchitectureArtifact,
        Path("schemas/portfolio/capability-record.schema.json"): CapabilityRecord,
        Path("schemas/portfolio/technology-record.schema.json"): TechnologyRecord,
        Path("schemas/portfolio/role-alignment.schema.json"): RoleAlignment,
        Path("schemas/portfolio/success-profile-evidence.schema.json"): SuccessProfileEvidence,
        Path("schemas/portfolio/evidence-index-record.schema.json"): EvidenceIndexRecord,
        Path("schemas/portfolio/run-registry.schema.json"): RunRegistry,
        Path("schemas/portfolio/portfolio-model-card.schema.json"): PortfolioModelCard,
        Path("schemas/portfolio/documentation-check.schema.json"): DocumentationCheck,
        Path("schemas/portfolio/cleanliness-check.schema.json"): CleanlinessCheck,
        Path("schemas/portfolio/repository-size-record.schema.json"): RepositorySizeRecord,
        Path("schemas/portfolio/release-gate-result.schema.json"): ReleaseGateResult,
        Path("schemas/portfolio/release-readiness.schema.json"): ReleaseReadinessReport,
        Path("schemas/portfolio/release-manifest.schema.json"): ReleaseManifest,
        Path("schemas/portfolio/release-package-manifest.schema.json"): ReleasePackageManifest,
    }
    for path, model in schema_map.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
    typer.echo("Schemas generated")


@app.command("contracts-inventory")
def contracts_inventory(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance/contracts"),
) -> None:
    """Generate current local contract inventory."""
    baseline = write_contract_inventory(output_dir)
    typer.echo(f"Contract inventory version: {baseline.contract_inventory_version}")
    typer.echo(f"Baseline ID: {baseline.baseline_id}")
    typer.echo(f"Total contract count: {baseline.contract_count}")
    typer.echo(f"Output directory: {output_dir}")


@app.command("contracts-baseline")
def contracts_baseline(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "tests/fixtures/assurance/contracts/baseline"
    ),
    confirm_baseline_update: Annotated[bool, typer.Option("--confirm-baseline-update")] = False,
) -> None:
    """Explicitly regenerate the checked-in contract baseline."""
    if not confirm_baseline_update:
        typer.echo("Baseline update requires --confirm-baseline-update", err=True)
        raise typer.Exit(code=1)
    baseline = write_contract_inventory(output_dir)
    typer.echo(f"Baseline ID: {baseline.baseline_id}")


@app.command("contracts-compare")
def contracts_compare(
    baseline_dir: Annotated[Path, typer.Option("--baseline-dir")] = Path(
        "tests/fixtures/assurance/contracts/baseline"
    ),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "reports/assurance/compatibility"
    ),
) -> None:
    """Compare current contracts against a baseline."""
    report = compare_contracts(baseline_dir, output_dir)
    typer.echo(f"Compatibility run ID: {report.compatibility_run_id}")
    typer.echo(f"Breaking changes: {report.breaking_change_count}")
    typer.echo(f"Overall status: {report.overall_compatibility_status}")
    if report.breaking_change_count:
        raise typer.Exit(code=1)


@app.command("contracts-validate")
def contracts_validate(
    compatibility_dir: Annotated[Path, typer.Option("--compatibility-dir")] = Path(
        "reports/assurance/compatibility"
    ),
) -> None:
    """Validate compatibility report status."""
    report = json.loads((compatibility_dir / "compatibility-report.json").read_text())
    typer.echo(f"Compatibility status: {report['overall_compatibility_status']}")
    if report["overall_compatibility_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("configuration-assurance")
def configuration_assurance(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Run local configuration assurance checks."""
    checks = write_configuration_assurance(load_settings(), output_dir)
    failed = [check for check in checks if check["status"] != "passed"]
    typer.echo(f"Configuration checks: {len(checks)}")
    typer.echo(f"Failed checks: {len(failed)}")
    if failed:
        raise typer.Exit(code=1)


@app.command("runtime-smoke-api")
def runtime_smoke_api(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=0, max=65535)] = 0,
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 30,
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/runtime-smoke"),
) -> None:
    """Run bounded local FastAPI smoke test."""
    report = run_api_smoke(host, port, timeout, output_dir)
    typer.echo(f"Smoke run ID: {report.smoke_run_id}")
    typer.echo(f"Overall status: {report.overall_status}")
    if report.overall_status != "passed":
        raise typer.Exit(code=1)


@app.command("runtime-smoke-dashboard")
def runtime_smoke_dashboard(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=0, max=65535)] = 0,
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 45,
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/runtime-smoke"),
) -> None:
    """Run bounded local Streamlit smoke test."""
    report = run_dashboard_smoke(host, port, timeout, output_dir)
    typer.echo(f"Smoke run ID: {report.smoke_run_id}")
    typer.echo(f"Overall status: {report.overall_status}")
    if report.overall_status != "passed":
        raise typer.Exit(code=1)


@app.command("runtime-smoke-summary")
def runtime_smoke_summary(
    smoke_dir: Annotated[Path, typer.Option("--smoke-dir")] = Path("reports/runtime-smoke"),
) -> None:
    """Print runtime smoke summary if available."""
    for name in ("api-smoke-report.json", "dashboard-smoke-report.json"):
        path = smoke_dir / name
        if path.exists():
            report = json.loads(path.read_text())
            typer.echo(f"{report['component']}: {report['overall_status']}")
        else:
            typer.echo(f"{name}: not_run")


@app.command("operational-integrity")
def operational_integrity(
    events_dir: Annotated[Path, typer.Option("--events-dir")] = Path(
        "tests/fixtures/observability"
    ),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "reports/assurance/observability"
    ),
) -> None:
    """Validate operational event integrity."""
    settings = load_settings()
    result = validate_operational_integrity(
        events_dir, output_dir, settings.milestone11.operational_event_quarantine_root
    )
    typer.echo(f"Accepted events: {result['accepted_event_count']}")
    typer.echo(f"Rejected events: {result['rejected_event_count']}")
    typer.echo(f"Overall status: {result['overall_status']}")
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("operational-quarantine-summary")
def operational_quarantine_summary(
    quarantine_dir: Annotated[Path, typer.Option("--quarantine-dir")] = Path(
        "outputs/observability/quarantine"
    ),
) -> None:
    """Print malformed-event quarantine summary."""
    summary = quarantine_summary(quarantine_dir)
    typer.echo(f"Quarantined files: {summary['quarantined_file_count']}")


@app.command("assurance-backup")
def assurance_backup(
    profile: Annotated[str, typer.Option("--profile")] = "portfolio-critical",
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/assurance/backups"),
) -> None:
    """Create deterministic selected evidence backup."""
    manifest = create_backup(profile, output_root)
    typer.echo(f"Backup ID: {manifest.backup_id}")
    typer.echo(f"Selected files: {manifest.selected_file_count}")


@app.command("assurance-backup-validate")
def assurance_backup_validate(
    backup_dir: Annotated[Path, typer.Option("--backup-dir")],
) -> None:
    """Validate deterministic backup manifest and checksums."""
    failures = validate_backup(backup_dir)
    if failures:
        for failure in failures:
            typer.echo(failure, err=True)
        raise typer.Exit(code=1)
    typer.echo("Backup validation passed")


@app.command("assurance-restore")
def assurance_restore(
    backup_dir: Annotated[Path, typer.Option("--backup-dir")],
    destination: Annotated[Path, typer.Option("--destination")],
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Restore selected backup to an explicit local destination."""
    manifest = restore_backup(backup_dir, destination, overwrite=overwrite)
    typer.echo(f"Restored files: {manifest.restored_file_count}")
    typer.echo(f"Checksum status: {manifest.checksum_status}")


@app.command("assurance-recovery-exercise")
def assurance_recovery_exercise(
    profile: Annotated[str, typer.Option("--profile")] = "portfolio-critical",
    output_root: Annotated[Path, typer.Option("--output-root")] = Path(
        "outputs/assurance/recovery"
    ),
) -> None:
    """Run local backup, restore, and validation exercise."""
    exercise = run_recovery_exercise(profile, output_root)
    typer.echo(f"Recovery run ID: {exercise.recovery_run_id}")
    typer.echo(f"Recovery status: {exercise.recovery_exercise_status}")


@app.command("security-assurance")
def security_assurance(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Run local security-control, secret, and sensitive-content assurance."""
    result = run_security_assurance(output_dir)
    typer.echo(f"Security assurance status: {result['overall_status']}")
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("dependency-inventory")
def dependency_inventory(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Generate offline dependency inventory."""
    inventory = write_dependency_inventory(output_dir)
    typer.echo(f"Dependency count: {inventory.dependency_count}")
    typer.echo(f"Policy violations: {len(inventory.policy_violations)}")
    if inventory.policy_violations:
        raise typer.Exit(code=1)


@app.command("sbom-generate")
def sbom_generate(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Generate local SBOM-style dependency evidence."""
    sbom = write_sbom(output_dir)
    typer.echo(f"SBOM ID: {sbom.sbom_id}")
    typer.echo(f"Component count: {len(sbom.components)}")


@app.command("container-assurance")
def container_assurance(
    dockerfile: Annotated[Path, typer.Option("--dockerfile")] = Path("Dockerfile"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Run static Dockerfile assurance checks."""
    result = run_container_assurance(dockerfile, output_dir)
    typer.echo(f"Container assurance status: {result['overall_status']}")
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("portfolio-assurance")
def portfolio_assurance(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/assurance"),
) -> None:
    """Generate final local portfolio assurance decision."""
    decision = generate_portfolio_assurance(load_settings(), output_dir)
    typer.echo(f"Assurance run ID: {decision.assurance_run_id}")
    typer.echo(f"Portfolio readiness status: {decision.portfolio_readiness_status}")
    typer.echo(f"Passed required gates: {decision.passed_required_gates}")
    typer.echo(f"Failed required gates: {decision.failed_required_gates}")
    if decision.failed_required_gates:
        raise typer.Exit(code=1)


@app.command("portfolio-assurance-validate")
def portfolio_assurance_validate(
    assurance_dir: Annotated[Path, typer.Option("--assurance-dir")] = Path("reports/assurance"),
) -> None:
    """Validate portfolio assurance decision evidence."""
    decision = json.loads((assurance_dir / "portfolio-assurance-decision.json").read_text())
    typer.echo(f"Portfolio readiness status: {decision['portfolio_readiness_status']}")
    if decision["failed_required_gates"]:
        raise typer.Exit(code=1)


@app.command("portfolio-assurance-summary")
def portfolio_assurance_summary(
    assurance_dir: Annotated[Path, typer.Option("--assurance-dir")] = Path("reports/assurance"),
) -> None:
    """Print local portfolio assurance summary."""
    decision = json.loads((assurance_dir / "portfolio-assurance-decision.json").read_text())
    typer.echo(f"Assurance run ID: {decision['assurance_run_id']}")
    typer.echo(f"Required gates: {decision['required_gate_count']}")
    typer.echo(f"Passed required gates: {decision['passed_required_gates']}")
    typer.echo(f"Failed required gates: {decision['failed_required_gates']}")
    typer.echo(f"Portfolio readiness status: {decision['portfolio_readiness_status']}")


@app.command("runtime-smoke-fixtures")
def runtime_smoke_fixtures(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "tests/fixtures/assurance/runtime-smoke"
    ),
) -> None:
    """Generate deterministic expected runtime smoke fixture contracts."""
    write_expected_smoke_fixtures(output_dir)
    typer.echo(f"Runtime smoke fixtures written: {output_dir}")


@app.command("portfolio-audit")
def portfolio_audit(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio/audit"),
) -> None:
    """Generate final repository audit evidence."""
    write_static_portfolio_docs()
    write_decisions()
    result = write_repository_audit(output_dir)
    typer.echo(f"Portfolio audit ID: {result['portfolio_audit_id']}")
    typer.echo(f"Failed items: {result['failed_items']}")
    if result["failed_items"]:
        raise typer.Exit(code=1)


@app.command("portfolio-audit-validate")
def portfolio_audit_validate(
    audit_dir: Annotated[Path, typer.Option("--audit-dir")] = Path("reports/portfolio/audit"),
) -> None:
    """Validate repository audit evidence."""
    result = json.loads((audit_dir / "repository-audit.json").read_text())
    typer.echo(f"Audit status: {result['audit_reconciliation_status']}")
    if result["audit_reconciliation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("milestones-audit")
def milestones_audit(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "reports/portfolio/milestones"
    ),
) -> None:
    """Audit milestone completeness from evidence."""
    result = write_milestone_audit(output_dir)
    typer.echo(
        f"Milestones complete: {result['milestones_complete']}/{result['milestones_audited']}"
    )
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("traceability-build")
def traceability_build(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "reports/portfolio/traceability"
    ),
) -> None:
    """Build cross-milestone traceability evidence."""
    result = write_traceability(output_dir)
    typer.echo(f"Traceability run ID: {result['traceability_run_id']}")
    typer.echo(f"Records: {result['traceability_record_count']}")


@app.command("traceability-validate")
def traceability_validate(
    traceability_dir: Annotated[Path, typer.Option("--traceability-dir")] = Path(
        "reports/portfolio/traceability"
    ),
) -> None:
    """Validate traceability evidence."""
    result = json.loads((traceability_dir / "traceability.json").read_text())
    typer.echo(f"Traceability status: {result['validation_status']}")
    if result["validation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("architecture-pack")
def architecture_pack(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path(
        "reports/portfolio/architecture"
    ),
) -> None:
    """Generate final architecture pack and Mermaid diagrams."""
    result = write_architecture_pack(output_dir)
    typer.echo(f"Architecture pack ID: {result['architecture_pack_id']}")
    typer.echo(f"Diagram count: {result['diagram_count']}")


@app.command("architecture-validate")
def architecture_validate(
    architecture_dir: Annotated[Path, typer.Option("--architecture-dir")] = Path(
        "reports/portfolio/architecture"
    ),
) -> None:
    """Validate final architecture pack."""
    result = json.loads((architecture_dir / "architecture-pack.json").read_text())
    typer.echo(f"Architecture validation status: {result['validation_status']}")
    if result["validation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("capability-map")
def capability_map(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate capability map."""
    result = write_capability_map(output_dir)
    typer.echo(f"Capability count: {result['capability_count']}")


@app.command("technology-map")
def technology_map(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate technology map."""
    result = write_technology_map(output_dir)
    typer.echo(f"Technology count: {result['technology_count']}")


@app.command("role-alignment")
def role_alignment(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate role and success-profile alignment."""
    result = write_role_alignment(output_dir)
    typer.echo(f"Role alignment count: {result['role_alignment_count']}")


@app.command("interview-pack")
def interview_pack(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("docs/interview"),
) -> None:
    """Generate final interview evidence pack."""
    result = write_interview_pack(output_dir)
    typer.echo(f"Interview pack status: {result['status']}")


@app.command("demo-pack")
def demo_pack(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("docs/demo"),
) -> None:
    """Generate final demonstration scripts."""
    result = write_demo_pack(output_dir)
    typer.echo(f"Demo pack status: {result['status']}")


@app.command("evidence-index")
def evidence_index(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate portfolio evidence index."""
    result = write_evidence_index(output_dir)
    typer.echo(f"Evidence index ID: {result['evidence_index_id']}")
    typer.echo(f"Evidence count: {result['evidence_count']}")
    if result["validation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("evidence-index-validate")
def evidence_index_validate(
    evidence_dir: Annotated[Path, typer.Option("--evidence-dir")] = Path("reports/portfolio"),
) -> None:
    """Validate evidence index."""
    result = json.loads((evidence_dir / "evidence-index.json").read_text())
    typer.echo(f"Evidence index status: {result['validation_status']}")
    if result["validation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("run-registry")
def run_registry_command(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate key run and approval registry."""
    registry = write_run_registry(output_dir)
    typer.echo(f"Run registry ID: {registry.registry_id}")


@app.command("portfolio-model-card")
def portfolio_model_card(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Generate final portfolio model card."""
    card = write_portfolio_model_card(output_dir)
    typer.echo(f"Portfolio model card ID: {card.model_card_id}")


@app.command("documentation-validate")
def documentation_validate() -> None:
    """Validate final reviewer-facing documentation."""
    result = validate_documentation()
    typer.echo(f"Documentation status: {result['overall_status']}")
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("repository-cleanliness")
def repository_cleanliness() -> None:
    """Remove disposable artifacts and write cleanliness report."""
    result = run_cleanliness()
    typer.echo(f"Repository cleanliness status: {result['overall_status']}")


@app.command("repository-size-audit")
def repository_size_audit(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/portfolio"),
) -> None:
    """Audit repository size and prohibited model weights."""
    result = run_size_audit(output_dir)
    typer.echo(f"Repository size status: {result['overall_status']}")
    if result["overall_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("release-readiness")
def release_readiness(
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/release"),
    reference_timestamp: Annotated[
        str, typer.Option("--reference-timestamp")
    ] = "2026-01-19T09:00:00+00:00",
) -> None:
    """Generate final release-readiness report."""
    report = write_release_readiness(output_dir, reference_timestamp)
    typer.echo(f"Release-readiness run ID: {report.release_readiness_run_id}")
    typer.echo(f"Release readiness status: {report.release_readiness_status}")
    if report.failed_required_gates:
        raise typer.Exit(code=1)


@app.command("release-readiness-validate")
def release_readiness_validate(
    readiness_dir: Annotated[Path, typer.Option("--readiness-dir")] = Path("reports/release"),
) -> None:
    """Validate release-readiness report."""
    report = json.loads((readiness_dir / "release-readiness.json").read_text())
    typer.echo(f"Release readiness status: {report['release_readiness_status']}")
    if report["failed_required_gates"]:
        raise typer.Exit(code=1)


@app.command("release-manifest")
def release_manifest(
    readiness_dir: Annotated[Path, typer.Option("--readiness-dir")] = Path("reports/release"),
    output_dir: Annotated[Path, typer.Option("--output-dir")] = Path("reports/release"),
    reference_timestamp: Annotated[
        str, typer.Option("--reference-timestamp")
    ] = "2026-01-20T09:00:00+00:00",
) -> None:
    """Generate deterministic release manifest."""
    manifest = write_release_manifest(readiness_dir, output_dir, reference_timestamp)
    typer.echo(f"Release ID: {manifest.release_id}")


@app.command("release-package")
def release_package(
    readiness_dir: Annotated[Path, typer.Option("--readiness-dir")] = Path("reports/release"),
    output_root: Annotated[Path, typer.Option("--output-root")] = Path("outputs/portfolio-release"),
    reference_timestamp: Annotated[
        str, typer.Option("--reference-timestamp")
    ] = "2026-01-20T09:00:00+00:00",
) -> None:
    """Create local reviewer-facing portfolio release package."""
    package = write_release_package(readiness_dir, output_root, reference_timestamp)
    typer.echo(f"Release ID: {package.release_id}")
    typer.echo(f"Package path: {package.package_output_path}")


@app.command("release-package-validate")
def release_package_validate(
    package_dir: Annotated[Path, typer.Option("--package-dir")],
) -> None:
    """Validate local release package."""
    result = validate_release_package(package_dir)
    typer.echo(f"Package validation status: {result['package_validation_status']}")
    if result["package_validation_status"] != "passed":
        raise typer.Exit(code=1)


@app.command("portfolio-final-summary")
def portfolio_final_summary() -> None:
    """Print final portfolio release summary."""
    summary = final_summary()
    for key, value in summary.items():
        typer.echo(f"{key}: {value}")
