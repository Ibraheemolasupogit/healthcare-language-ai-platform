"""Typed application configuration loading."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from healthcare_language_ai.constants import APPLICATION_NAME, ENV_PREFIX
from healthcare_language_ai.domain.enums import ClinicalDocumentType
from healthcare_language_ai.exceptions import ConfigurationError, DataGovernanceError
from healthcare_language_ai.utils.time import require_timezone_aware


class SyntheticGenerationSettings(BaseModel):
    """Settings for deterministic synthetic document generation."""

    default_record_count: int = Field(default=15, gt=0)
    allowed_document_types: list[ClinicalDocumentType] = Field(
        default_factory=lambda: list(ClinicalDocumentType)
    )
    reference_timestamp: datetime = datetime.fromisoformat("2026-01-01T09:00:00+00:00")
    generator_seed: int = 2026
    generator_version: str = "1.0.0"
    template_version: str = "1.0.0"
    vocabulary_version: str = "1.0.0"
    maximum_records_per_run: int = Field(default=500, ge=1, le=10_000)
    output_format: Literal["jsonl"] = "jsonl"
    include_annotations: bool = True

    @field_validator("reference_timestamp")
    @classmethod
    def reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "reference_timestamp")

    @field_validator("allowed_document_types")
    @classmethod
    def allowed_document_types_must_not_be_empty(
        cls, value: list[ClinicalDocumentType]
    ) -> list[ClinicalDocumentType]:
        if not value:
            msg = "allowed_document_types must not be empty"
            raise ValueError(msg)
        return value


class IngestionSettings(BaseModel):
    """Settings for local deterministic ingestion."""

    default_ingestion_mode: Literal["strict", "quarantine"] = "strict"
    default_output_root: Path = Path("outputs/ingestion")
    ingestion_reference_timestamp: datetime = datetime.fromisoformat("2026-01-02T09:00:00+00:00")
    maximum_source_records: int = Field(default=1_000, gt=0)
    allowed_source_roots: list[Path] = Field(
        default_factory=lambda: [Path("tests/fixtures"), Path("outputs")]
    )
    follow_symlinks: bool = False
    default_overwrite_policy: Literal["fail_if_exists", "replace_identical", "force_replace"] = (
        "fail_if_exists"
    )
    write_csv: bool = True
    write_parquet: bool = True
    csv_null_value: str = ""
    parquet_compression: Literal["zstd", "snappy", "none"] = "zstd"
    ingestion_contract_version: str = "1.0.0"
    snowflake_contract_version: str = "1.0.0"
    snowflake_target_database: str = "HEALTHCARE_LANGUAGE_AI"
    snowflake_raw_schema: str = "RAW"
    snowflake_staging_schema: str = "STAGING"
    snowflake_governance_schema: str = "GOVERNANCE"

    @field_validator("ingestion_reference_timestamp")
    @classmethod
    def ingestion_reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "ingestion_reference_timestamp")


class PreprocessingSettings(BaseModel):
    """Settings for deterministic local text preprocessing."""

    default_preprocessing_mode: Literal["conservative", "analytical"] = "conservative"
    default_output_root: Path = Path("outputs/preprocessing")
    preprocessing_reference_timestamp: datetime = datetime.fromisoformat(
        "2026-01-03T09:00:00+00:00"
    )
    maximum_documents_per_run: int = Field(default=1_000, gt=0)
    allowed_ingestion_roots: list[Path] = Field(
        default_factory=lambda: [Path("tests/fixtures/ingestion"), Path("outputs/ingestion")]
    )
    follow_symlinks: bool = False
    default_overwrite_policy: Literal["fail_if_exists", "replace_identical", "force_replace"] = (
        "fail_if_exists"
    )
    write_csv: bool = True
    write_parquet: bool = True
    unicode_normalisation_form: Literal["NFC", "NFKC"] = "NFC"
    tab_width: int = Field(default=4, gt=0, le=8)
    collapse_repeated_spaces: bool = True
    preserve_final_newline: bool = True
    maximum_sentence_length: int = Field(default=500, gt=0)
    minimum_document_length: int = Field(default=80, gt=0)
    preprocessing_contract_version: str = "1.0.0"
    normalisation_version: str = "1.0.0"
    section_parser_version: str = "1.0.0"
    sentence_segmenter_version: str = "1.0.0"
    tokeniser_version: str = "1.0.0"
    quality_rules_version: str = "1.0.0"
    databricks_contract_version: str = "1.0.0"
    databricks_catalog_placeholder: str = "hla_catalog_placeholder"
    databricks_bronze_schema: str = "bronze"
    databricks_silver_schema: str = "silver"
    databricks_gold_schema: str = "gold"

    @field_validator("preprocessing_reference_timestamp")
    @classmethod
    def preprocessing_reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "preprocessing_reference_timestamp")


class ExtractionSettings(BaseModel):
    """Settings for deterministic local rule-based extraction."""

    default_output_root: Path = Path("outputs/extraction")
    extraction_reference_timestamp: datetime = datetime.fromisoformat("2026-01-04T09:00:00+00:00")
    maximum_documents_per_extraction_run: int = Field(default=1_000, gt=0)
    allowed_preprocessing_roots: list[Path] = Field(
        default_factory=lambda: [
            Path("tests/fixtures/preprocessing"),
            Path("outputs/preprocessing"),
        ]
    )
    default_text_representation: Literal["normalised_text"] = "normalised_text"
    case_sensitive_matching: bool = False
    word_boundary_required: bool = True
    allow_overlapping_predictions: bool = False
    default_overwrite_policy: Literal["fail_if_exists", "replace_identical", "force_replace"] = (
        "fail_if_exists"
    )
    write_csv: bool = True
    write_parquet: bool = True
    extraction_contract_version: str = "1.0.0"
    entity_rule_version: str = "1.0.0"
    classification_rule_version: str = "1.0.0"
    overlap_resolution_version: str = "1.0.0"
    vocabulary_version: str = "1.0.0"

    @field_validator("extraction_reference_timestamp")
    @classmethod
    def extraction_reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "extraction_reference_timestamp")


class EvaluationSettings(BaseModel):
    """Settings for deterministic local baseline evaluation."""

    default_output_root: Path = Path("outputs/evaluation")
    evaluation_reference_timestamp: datetime = datetime.fromisoformat("2026-01-05T09:00:00+00:00")
    default_matching_policy: Literal["exact", "exact_normalised_value", "relaxed_overlap"] = "exact"
    relaxed_overlap_threshold: float = Field(default=0.5, ge=0, le=1)
    context_window_characters: int = Field(default=32, ge=0, le=200)
    maximum_error_records: int = Field(default=1_000, ge=0)
    default_overwrite_policy: Literal["fail_if_exists", "replace_identical", "force_replace"] = (
        "fail_if_exists"
    )
    write_csv: bool = True
    write_parquet: bool = True
    evaluation_contract_version: str = "1.0.0"
    metrics_version: str = "1.0.0"
    error_analysis_version: str = "1.0.0"
    mlflow_contract_version: str = "1.0.0"

    @field_validator("evaluation_reference_timestamp")
    @classmethod
    def evaluation_reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "evaluation_reference_timestamp")


class RetrievalSettings(BaseModel):
    """Settings for deterministic local retrieval experiments."""

    default_index_output_root: Path = Path("outputs/retrieval/indexes")
    default_retrieval_output_root: Path = Path("outputs/retrieval/runs")
    default_retrieval_evaluation_output_root: Path = Path("outputs/retrieval/evaluation")
    index_reference_timestamp: datetime = datetime.fromisoformat("2026-01-06T09:00:00+00:00")
    retrieval_reference_timestamp: datetime = datetime.fromisoformat("2026-01-07T09:00:00+00:00")
    retrieval_evaluation_reference_timestamp: datetime = datetime.fromisoformat(
        "2026-01-08T09:00:00+00:00"
    )
    maximum_retrieval_units: int = Field(default=10_000, gt=0)
    maximum_queries: int = Field(default=500, gt=0)
    default_unit_types: Literal["document", "section", "sentence", "all"] = "all"
    default_text_representation: Literal["normalised_text"] = "normalised_text"
    default_retrieval_strategy: Literal["keyword", "tfidf", "bm25", "hybrid"] = "hybrid"
    default_top_k: int = Field(default=5, gt=0)
    evaluation_k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])
    corpus_version: str = "1.0.0"
    retrieval_contract_version: str = "1.0.0"
    tokeniser_version: str = "1.0.0"
    keyword_version: str = "1.0.0"
    tfidf_version: str = "1.0.0"
    bm25_version: str = "1.0.0"
    hash_embedding_version: str = "1.0.0"
    hybrid_version: str = "1.0.0"
    retrieval_evaluation_contract_version: str = "1.0.0"
    retrieval_metrics_version: str = "1.0.0"
    retrieval_failure_version: str = "1.0.0"
    embedding_dimension: int = Field(default=32, gt=0)
    hash_ngram_min: int = Field(default=1, gt=0)
    hash_ngram_max: int = Field(default=2, gt=0)
    bm25_k1: float = Field(default=1.5, gt=0)
    bm25_b: float = Field(default=0.75, ge=0, le=1)
    keyword_weight: float = Field(default=0.15, ge=0)
    tfidf_weight: float = Field(default=0.25, ge=0)
    bm25_weight: float = Field(default=0.4, ge=0)
    dense_weight: float = Field(default=0.15, ge=0)
    metadata_weight: float = Field(default=0.05, ge=0)
    relaxed_filter_policy: Literal["pre_filter"] = "pre_filter"
    snippet_character_limit: int = Field(default=96, gt=0, le=500)
    default_overwrite_policy: Literal["fail_if_exists", "replace_identical", "force_replace"] = (
        "fail_if_exists"
    )
    vector_search_contract_version: str = "1.0.0"

    @field_validator(
        "index_reference_timestamp",
        "retrieval_reference_timestamp",
        "retrieval_evaluation_reference_timestamp",
    )
    @classmethod
    def retrieval_timestamps_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "retrieval timestamp")

    @field_validator("evaluation_k_values")
    @classmethod
    def k_values_must_be_unique_positive(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value) or len(value) != len(set(value)):
            msg = "evaluation_k_values must be unique positive integers"
            raise ValueError(msg)
        return sorted(value)

    @field_validator("hash_ngram_max")
    @classmethod
    def ngram_max_must_be_valid(cls, value: int, info) -> int:  # type: ignore[no-untyped-def]
        ngram_min = info.data.get("hash_ngram_min", 1)
        if value < ngram_min:
            msg = "hash_ngram_max must be greater than or equal to hash_ngram_min"
            raise ValueError(msg)
        return value

    @field_validator("metadata_weight")
    @classmethod
    def at_least_one_weight_must_be_positive(cls, value: float, info) -> float:  # type: ignore[no-untyped-def]
        weights = [
            info.data.get("keyword_weight", 0),
            info.data.get("tfidf_weight", 0),
            info.data.get("bm25_weight", 0),
            info.data.get("dense_weight", 0),
            value,
        ]
        if not any(weight > 0 for weight in weights):
            msg = "at least one retrieval fusion weight must be positive"
            raise ValueError(msg)
        return value


class Milestone10Settings(BaseModel):
    """Settings for local-only Milestone 10 demonstration services."""

    api_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_reload: bool = False
    api_docs_enabled: bool = True
    cors_enabled: bool = False
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1"])
    maximum_query_characters: int = Field(default=500, ge=1, le=5000)
    maximum_metadata_filters: int = Field(default=8, ge=0, le=50)
    maximum_trace_depth: int = Field(default=25, ge=1, le=100)
    streamlit_enabled: bool = True
    streamlit_host: str = "127.0.0.1"
    streamlit_port: int = Field(default=8501, ge=1, le=65535)
    streamlit_service_mode: Literal["direct", "local_api"] = "direct"
    operational_events_enabled: bool = True
    operational_event_root: Path = Path("outputs/observability/events")
    operational_event_max_bytes: int = Field(default=250_000, ge=1024)
    operational_event_retention_files: int = Field(default=5, ge=1)
    prometheus_metrics_enabled: bool = True
    readiness_validate_fixtures: bool = True
    demo_report_root: Path = Path("reports/demo")
    portfolio_report_root: Path = Path("reports/portfolio")
    application_service_version: str = "1.0.0"
    api_contract_version: str = "1.0.0"
    api_version: str = "v1"
    streamlit_demo_version: str = "1.0.0"
    observability_contract_version: str = "1.0.0"
    operational_event_version: str = "1.0.0"
    metric_aggregation_version: str = "1.0.0"
    readiness_version: str = "1.0.0"
    demo_session_version: str = "1.0.0"
    portfolio_summary_version: str = "1.0.0"

    @field_validator("api_host", "streamlit_host")
    @classmethod
    def default_hosts_are_local(cls, value: str) -> str:
        if value == "0.0.0.0":
            msg = "default local service hosts must not bind to 0.0.0.0"
            raise ValueError(msg)
        return value


class Milestone11Settings(BaseModel):
    """Settings for local Milestone 11 assurance and resilience controls."""

    query_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    retrieval_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    rag_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    trace_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    readiness_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    maximum_concurrent_queries: int = Field(default=8, ge=1, le=100)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=30, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    allow_unsafe_local_binding: bool = False
    contract_baseline_root: Path = Path("tests/fixtures/assurance/contracts/baseline")
    contract_compatibility_required: bool = True
    operational_event_checksum_enabled: bool = True
    operational_event_quarantine_root: Path = Path("outputs/observability/quarantine")
    backup_output_root: Path = Path("outputs/assurance/backups")
    backup_allowed_roots: list[Path] = Field(
        default_factory=lambda: [
            Path("config"),
            Path("schemas"),
            Path("tests/fixtures"),
            Path("reports/portfolio"),
        ]
    )
    restore_allowed_roots: list[Path] = Field(
        default_factory=lambda: [Path("outputs/assurance/restored"), Path("/tmp")]
    )
    runtime_smoke_enabled: bool = True
    runtime_smoke_timeout_seconds: int = Field(default=30, ge=1, le=180)
    runtime_smoke_api_port: int = Field(default=0, ge=0, le=65535)
    runtime_smoke_dashboard_port: int = Field(default=0, ge=0, le=65535)
    secret_scan_enabled: bool = True
    dependency_inventory_enabled: bool = True
    sbom_enabled: bool = True
    container_assurance_enabled: bool = True
    portfolio_assurance_version: str = "1.0.0"
    contract_inventory_version: str = "1.0.0"
    compatibility_policy_version: str = "1.0.0"
    configuration_assurance_version: str = "1.0.0"
    lifecycle_version: str = "1.0.0"
    rate_limit_version: str = "1.0.0"
    timeout_policy_version: str = "1.0.0"
    runtime_smoke_version: str = "1.0.0"
    operational_integrity_version: str = "1.0.0"
    backup_contract_version: str = "1.0.0"
    recovery_contract_version: str = "1.0.0"
    security_assurance_version: str = "1.0.0"
    dependency_inventory_version: str = "1.0.0"
    sbom_version: str = "1.0.0"
    container_assurance_version: str = "1.0.0"

    @field_validator("backup_allowed_roots", "restore_allowed_roots")
    @classmethod
    def roots_must_be_local(cls, value: list[Path]) -> list[Path]:
        if not value:
            msg = "at least one local root must be configured"
            raise ValueError(msg)
        return value


class Milestone12Settings(BaseModel):
    """Settings for final local portfolio packaging and release evidence."""

    portfolio_report_root: Path = Path("reports/portfolio")
    release_report_root: Path = Path("reports/release")
    portfolio_release_root: Path = Path("outputs/portfolio-release")
    source_tree_excluded_paths: list[str] = Field(
        default_factory=lambda: [
            ".git",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            ".venv",
            "htmlcov",
        ]
    )
    maximum_allowed_file_bytes: int = Field(default=10_000_000, gt=0)
    documentation_link_validation_enabled: bool = True
    mermaid_validation_enabled: bool = True
    release_reference_timestamp: datetime = datetime.fromisoformat("2026-01-20T09:00:00+00:00")
    required_milestones: list[str] = Field(default_factory=lambda: [f"M{i}" for i in range(1, 12)])
    required_documentation_files: list[Path] = Field(
        default_factory=lambda: [
            Path("docs/REVIEWER_GUIDE.md"),
            Path("docs/FINAL_LIMITATIONS.md"),
            Path("docs/milestones/milestone-12.md"),
        ]
    )
    required_release_gates: list[str] = Field(
        default_factory=lambda: [
            "tests",
            "contracts",
            "retrieval_approval",
            "rag_approval",
            "portfolio_assurance",
            "documentation",
            "limitations",
            "evidence_index",
            "model_card",
            "runtime_smoke",
            "backup_recovery",
            "security",
            "dependency",
            "container",
        ]
    )
    release_contract_version: str = "1.0.0"
    portfolio_contract_version: str = "1.0.0"
    repository_audit_version: str = "1.0.0"
    milestone_audit_version: str = "1.0.0"
    traceability_version: str = "1.0.0"
    architecture_pack_version: str = "1.0.0"
    capability_map_version: str = "1.0.0"
    technology_map_version: str = "1.0.0"
    role_alignment_version: str = "1.0.0"
    interview_pack_version: str = "1.0.0"
    demo_pack_version: str = "1.0.0"
    evidence_index_version: str = "1.0.0"
    portfolio_model_card_version: str = "1.0.0"
    documentation_validation_version: str = "1.0.0"
    repository_cleanliness_version: str = "1.0.0"
    release_readiness_version: str = "1.0.0"
    release_manifest_version: str = "1.0.0"
    release_package_version: str = "1.0.0"

    @field_validator("release_reference_timestamp")
    @classmethod
    def release_reference_timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, "release_reference_timestamp")


class AppSettings(BaseSettings):
    """Application settings with safe defaults for local synthetic-data work."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    application_name: str = APPLICATION_NAME
    environment: str = "local"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    data_root: Path = Path("data")
    output_root: Path = Path("outputs")
    report_root: Path = Path("reports")
    synthetic_data_only: bool = True
    max_document_text_length: int = Field(default=20_000, gt=0)
    deterministic_seed: int = 42
    synthetic_generation: SyntheticGenerationSettings = Field(
        default_factory=SyntheticGenerationSettings
    )
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    preprocessing: PreprocessingSettings = Field(default_factory=PreprocessingSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    milestone10: Milestone10Settings = Field(default_factory=Milestone10Settings)
    milestone11: Milestone11Settings = Field(default_factory=Milestone11Settings)
    milestone12: Milestone12Settings = Field(default_factory=Milestone12Settings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Place environment sources above YAML-provided init values."""
        return env_settings, dotenv_settings, init_settings, file_secret_settings

    @field_validator("log_level")
    @classmethod
    def log_level_is_known(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            msg = f"log_level must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return normalized

    @field_validator("synthetic_data_only")
    @classmethod
    def enforce_synthetic_only(cls, value: bool) -> bool:
        if not value:
            msg = "synthetic_data_only must remain enabled in this portfolio implementation"
            raise DataGovernanceError(msg)
        return value

    def sanitized(self) -> dict[str, Any]:
        """Return configuration suitable for CLI display and logs."""
        return {
            "application_name": self.application_name,
            "environment": self.environment,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "data_root": str(self.data_root),
            "output_root": str(self.output_root),
            "report_root": str(self.report_root),
            "synthetic_data_only": self.synthetic_data_only,
            "max_document_text_length": self.max_document_text_length,
            "deterministic_seed": self.deterministic_seed,
            "synthetic_generation": self.synthetic_generation.model_dump(mode="json"),
            "ingestion": self.ingestion.model_dump(mode="json"),
            "preprocessing": self.preprocessing.model_dump(mode="json"),
            "extraction": self.extraction.model_dump(mode="json"),
            "evaluation": self.evaluation.model_dump(mode="json"),
            "retrieval": self.retrieval.model_dump(mode="json"),
            "milestone10": self.milestone10.model_dump(mode="json"),
            "milestone11": self.milestone11.model_dump(mode="json"),
            "milestone12": self.milestone12.model_dump(mode="json"),
        }


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        msg = f"Configuration file not found: {path}"
        raise ConfigurationError(msg)
    try:
        with path.open("r", encoding="utf-8") as stream:
            loaded = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        msg = f"Configuration file is malformed YAML: {path}"
        raise ConfigurationError(msg) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        msg = f"Configuration file must contain a mapping: {path}"
        raise ConfigurationError(msg)
    return loaded


def load_settings(config_path: Path | None = None) -> AppSettings:
    """Load settings from defaults, optional YAML, environment, and optional .env.

    Precedence is: code defaults, YAML values, then environment variables and .env
    values handled by pydantic-settings.
    """
    yaml_values = _load_yaml_mapping(config_path) if config_path is not None else {}
    try:
        return AppSettings(**yaml_values)
    except DataGovernanceError:
        raise
    except PydanticValidationError as exc:
        msg = "Configuration is structurally invalid"
        raise ConfigurationError(msg) from exc


def validate_local_environment(settings: AppSettings) -> list[Path]:
    """Ensure required local directories exist and synthetic-only mode is enabled."""
    if not settings.synthetic_data_only:
        msg = "Synthetic-data-only mode must be enabled"
        raise DataGovernanceError(msg)

    created_or_available: list[Path] = []
    for directory in (settings.data_root, settings.output_root, settings.report_root):
        resolved = directory.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        if not resolved.is_dir():
            msg = f"Configured path is not a directory: {resolved}"
            raise ConfigurationError(msg)
        created_or_available.append(resolved)
    return created_or_available
