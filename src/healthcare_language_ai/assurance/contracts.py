"""Typed contracts for local portfolio assurance."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssuranceBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractInventoryRecord(AssuranceBaseModel):
    contract_id: str
    contract_type: str
    contract_version: str = "1.0.0"
    location: str
    owner_module: str
    stability: Literal["experimental", "stable", "deprecated", "internal"] = "stable"
    compatibility_policy: str = "stable_contract_v1"
    introduced_milestone: str = "M11"
    deprecated: bool = False
    replacement_contract_id: str = ""
    checksum: str


class ContractBaseline(AssuranceBaseModel):
    baseline_id: str
    contract_inventory_version: str = "1.0.0"
    contract_count: int
    pydantic_contract_count: int
    json_schema_count: int
    api_route_count: int
    cli_command_count: int
    prompt_contract_count: int
    configuration_section_count: int
    stable_contract_count: int
    experimental_contract_count: int
    deprecated_contract_count: int
    checksum: str


class ContractChange(AssuranceBaseModel):
    change_id: str
    contract_id: str
    change_type: str
    field_path: str = ""
    before_value: str = ""
    after_value: str = ""
    compatibility: Literal["backward_compatible", "conditionally_compatible", "breaking", "unknown"]
    reason: str


class CompatibilityReport(AssuranceBaseModel):
    compatibility_run_id: str
    baseline_id: str
    current_inventory_id: str
    added_contract_count: int
    removed_contract_count: int
    changed_contract_count: int
    backward_compatible_change_count: int
    conditionally_compatible_change_count: int
    breaking_change_count: int
    unknown_change_count: int
    api_breaking_change_count: int
    cli_breaking_change_count: int
    configuration_breaking_change_count: int
    compatibility_policy_version: str = "1.0.0"
    overall_compatibility_status: Literal["passed", "failed"]
    output_checksum_status: Literal["passed", "failed"] = "passed"
    changes: list[ContractChange] = Field(default_factory=list)


class CliCommandContract(AssuranceBaseModel):
    command_name: str
    required_arguments: list[str] = Field(default_factory=list)
    optional_arguments: list[str] = Field(default_factory=list)
    external_connection_permitted: bool = False


class ConfigurationContract(AssuranceBaseModel):
    section: str
    keys: list[str]
    safe_defaults: bool


class DeprecationRecord(AssuranceBaseModel):
    contract_id: str
    deprecated_since: str
    removal_not_before: str
    replacement: str
    migration_guidance: str
    warning_message: str


class ComponentReadiness(AssuranceBaseModel):
    component: str
    status: Literal["healthy", "degraded", "unavailable"]
    required: bool
    message: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RuntimeSmokeCase(AssuranceBaseModel):
    case_id: str
    component: Literal["api", "dashboard"]
    host: str
    port: int
    timeout_seconds: int


class RuntimeSmokeReport(AssuranceBaseModel):
    smoke_run_id: str
    component: Literal["api", "dashboard"]
    process_started: bool
    local_host: str
    local_port: int
    liveness_status: str
    readiness_status: str = "not_applicable"
    http_smoke_status: str
    synthetic_query_status: str = "not_applicable"
    prohibited_query_refusal_status: str = "not_applicable"
    security_header_status: str = "not_applicable"
    process_termination_status: str
    browser_interaction_performed: bool = False
    duration_seconds: float
    overall_status: Literal["passed", "failed", "blocked"]
    output_path: str


class OperationalEventManifest(AssuranceBaseModel):
    event_file: str
    sequence_start: int
    sequence_end: int
    event_count: int
    file_size: int
    checksum: str
    created_at: datetime
    closed_at: datetime
    rotation_reason: str = "active_file"


class MalformedEventRecord(AssuranceBaseModel):
    source_file: str
    line_number: int
    reason: str
    quarantined_path: str


class BackupSelection(AssuranceBaseModel):
    profile: str
    selected_paths: list[str]


class BackupManifest(AssuranceBaseModel):
    backup_id: str
    backup_contract_version: str = "1.0.0"
    profile: str
    selected_file_count: int
    files: dict[str, str]
    checksum: str
    credential_exclusion_status: Literal["passed", "failed"] = "passed"


class RestoreManifest(AssuranceBaseModel):
    backup_id: str
    destination: str
    restored_file_count: int
    checksum_status: Literal["passed", "failed"]
    path_traversal_validation: Literal["passed", "failed"]
    symlink_validation: Literal["passed", "failed"]


class RecoveryExercise(AssuranceBaseModel):
    recovery_run_id: str
    backup_id: str
    restore_manifest: RestoreManifest
    restored_contract_validation: str
    restored_retrieval_approval_validation: str
    restored_rag_approval_validation: str
    restored_rag_fixture_validation: str
    recovery_exercise_status: Literal["passed", "failed"]


class SecurityControlCheck(AssuranceBaseModel):
    check_id: str
    description: str
    status: Literal["passed", "failed", "blocked"]
    required: bool = True
    message: str = ""


class DependencyRecord(AssuranceBaseModel):
    package_name: str
    installed_version: str
    dependency_group: str
    direct: bool
    runtime: bool
    license_metadata: str = ""
    source_metadata: str = ""


class DependencyInventory(AssuranceBaseModel):
    dependency_inventory_id: str
    dependency_inventory_version: str = "1.0.0"
    records: list[DependencyRecord]
    dependency_count: int
    direct_dependency_count: int
    development_dependency_count: int
    policy_violations: list[str] = Field(default_factory=list)


class SbomDocument(AssuranceBaseModel):
    sbom_id: str
    sbom_version: str = "1.0.0"
    sbom_format: str = "CycloneDX-like-local"
    components: list[DependencyRecord]
    vulnerability_status: str = "not_evaluated_offline_inventory_only"


class ContainerAssuranceCheck(AssuranceBaseModel):
    check_id: str
    status: Literal["passed", "failed", "blocked"]
    message: str


class AssuranceGateResult(AssuranceBaseModel):
    gate_id: str
    required: bool
    status: Literal["passed", "failed", "conditional", "blocked"]
    evidence: str


class PortfolioAssuranceDecision(AssuranceBaseModel):
    assurance_run_id: str
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    conditional_gate_count: int
    portfolio_readiness_status: Literal[
        "ready_for_local_portfolio_demonstration", "conditionally_ready", "not_ready"
    ]
    ready_for_local_portfolio_demonstration: bool
    production_ready: bool = False
    clinically_ready: bool = False
    cloud_deployment_approved: bool = False
    known_blocked_checks: list[str] = Field(default_factory=list)
    known_degraded_components: list[str] = Field(default_factory=list)
    gates: list[AssuranceGateResult] = Field(default_factory=list)
