"""Typed contracts for final portfolio packaging evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AuditStatus = Literal["passed", "warning", "failed", "not_applicable"]
ReleaseStatus = Literal["ready_for_portfolio_release", "conditionally_ready", "not_ready"]


class RepositoryAuditRecord(BaseModel):
    audit_item_id: str
    category: str
    item: str
    expected: str
    actual: str
    status: AuditStatus
    evidence_path: str
    milestone: str
    severity: Literal["info", "low", "medium", "high"] = "info"
    message: str = ""


class MilestoneAudit(BaseModel):
    milestone: str
    objective: str
    implemented_capabilities: list[str]
    primary_modules: list[str]
    primary_commands: list[str]
    fixture_evidence: list[str]
    validation_evidence: list[str]
    known_limitations: list[str]
    completion_status: AuditStatus


class TraceabilityRecord(BaseModel):
    requirement_id: str
    capability: str
    source_module: str
    test_reference: str
    fixture_reference: str
    documentation_reference: str
    interface_reference: str
    assurance_reference: str
    status: AuditStatus


class ArchitectureArtifact(BaseModel):
    artifact_id: str
    title: str
    artifact_type: Literal["document", "diagram"]
    path: str
    status: AuditStatus


class CapabilityRecord(BaseModel):
    capability_id: str
    capability: str
    status: AuditStatus
    implemented_evidence: str
    technology: str
    milestone: str
    demonstration_path: str
    known_limitation: str


class TechnologyRecord(BaseModel):
    technology_id: str
    technology: str
    role: str
    status: Literal["implemented_locally", "optional_local", "contract_only", "not_implemented"]
    evidence_path: str
    limitation: str


class RoleAlignment(BaseModel):
    role_id: str
    role: str
    relevant_capabilities: list[str]
    evidence_paths: list[str]
    demonstration_examples: list[str]
    technical_discussion_points: list[str]
    limitations: list[str]


class SuccessProfileEvidence(BaseModel):
    behaviour_id: str
    behaviour: str
    evidence_paths: list[str]
    summary: str


class InterviewEvidence(BaseModel):
    interview_pack_version: str = "1.0.0"
    documents: list[str]
    status: AuditStatus


class DemoScenario(BaseModel):
    scenario_id: str
    title: str
    path: str
    status: AuditStatus


class ReviewerPath(BaseModel):
    path_id: str
    title: str
    duration_minutes: int
    documents: list[str]


class EvidenceIndexRecord(BaseModel):
    evidence_id: str
    title: str
    category: str
    milestone: str
    path: str
    description: str
    status: AuditStatus
    checksum: str
    related_ids: list[str] = Field(default_factory=list)


class RunRegistry(BaseModel):
    registry_id: str
    synthetic_dataset_id: str
    ingestion_run_id: str
    preprocessing_run_id: str
    extraction_run_id: str
    entity_evaluation_run_id: str
    retrieval_index_id: str
    retrieval_run_ids: list[str]
    retrieval_evaluation_ids: list[str]
    holdout_dataset_id: str
    retrieval_comparison_ids: list[str]
    retrieval_approval_id: str
    rag_run_id: str
    rag_evaluation_id: str
    rag_approval_status: str
    demo_session_id: str
    contract_baseline_id: str
    compatibility_run_id: str
    backup_id: str
    portfolio_assurance_id: str


class PortfolioModelCard(BaseModel):
    model_card_id: str
    system_purpose: str
    intended_users: list[str]
    intended_uses: list[str]
    out_of_scope_uses: list[str]
    data: str
    models_and_non_model_components: list[str]
    retrieval: str
    rag: str
    safety_controls: list[str]
    evaluation: list[str]
    approvals: list[str]
    api: str
    dashboard: str
    observability: str
    security_assurance: str
    supply_chain_assurance: str
    limitations: list[str]
    ethical_considerations: list[str]
    privacy_position: str
    clinical_use_prohibition: bool
    future_work: list[str]


class DocumentationCheck(BaseModel):
    check_id: str
    path: str
    check_type: str
    status: AuditStatus
    message: str = ""


class CleanlinessCheck(BaseModel):
    check_id: str
    path: str
    status: AuditStatus
    action: str
    message: str = ""


class RepositorySizeRecord(BaseModel):
    path: str
    size_bytes: int
    category: str
    status: AuditStatus
    message: str = ""


class ReleaseGateResult(BaseModel):
    gate_id: str
    required: bool
    status: AuditStatus
    evidence: str
    message: str = ""


class ReleaseReadinessReport(BaseModel):
    release_readiness_run_id: str
    release_readiness_version: str = "1.0.0"
    required_gate_count: int
    passed_required_gates: int
    failed_required_gates: int
    conditional_gate_count: int
    test_count: int
    coverage: float
    release_readiness_status: ReleaseStatus
    ready_for_portfolio_release: bool
    production_ready: bool = False
    clinically_validated: bool = False
    cloud_deployed: bool = False
    output_checksum_status: Literal["passed", "failed"] = "passed"
    gates: list[ReleaseGateResult]


class ReleaseManifest(BaseModel):
    release_id: str
    release_version: str
    repository_name: str
    release_scope: str
    milestones_completed: list[str]
    test_count: int
    coverage: float
    contract_baseline_id: str
    retrieval_approval_id: str
    rag_run_id: str
    rag_evaluation_id: str
    demo_session_id: str
    assurance_run_id: str
    release_readiness_status: ReleaseStatus
    evidence_index_checksum: str
    portfolio_model_card_checksum: str
    architecture_pack_checksum: str
    documentation_checksum: str
    fixture_manifest_checksum: str
    source_tree_checksum: str
    created_at: str
    synthetic_data_only: bool = True
    clinical_use_prohibited: bool = True
    production_ready: bool = False
    clinically_validated: bool = False
    cloud_deployed: bool = False


class ReleasePackageManifest(BaseModel):
    release_id: str
    release_version: str
    release_scope: str
    milestones_included: list[str]
    selected_file_count: int
    source_tree_file_count: int
    evidence_index_checksum: str
    portfolio_model_card_checksum: str
    architecture_pack_checksum: str
    documentation_checksum: str
    fixture_manifest_checksum: str
    source_tree_checksum: str
    package_checksum_status: Literal["passed", "failed"]
    credential_exclusion_status: Literal["passed", "failed"]
    mutable_log_exclusion_status: Literal["passed", "failed"]
    model_weight_exclusion_status: Literal["passed", "failed"]
    package_validation_status: Literal["passed", "failed"]
    package_output_path: str
