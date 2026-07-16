"""Health and readiness checks for the local demonstration layer."""

from __future__ import annotations

from healthcare_language_ai import __version__
from healthcare_language_ai.application.approval_service import ApprovalService
from healthcare_language_ai.application.contracts import (
    HealthResponse,
    ReadinessCheck,
    ReadinessResponse,
    SystemStatusResponse,
)
from healthcare_language_ai.application.evidence_service import EvidenceService
from healthcare_language_ai.config import AppSettings
from healthcare_language_ai.constants import APPLICATION_NAME


class HealthService:
    def __init__(
        self, settings: AppSettings, approval: ApprovalService, evidence: EvidenceService
    ) -> None:
        self.settings = settings
        self.approval = approval
        self.evidence = evidence

    def live(self) -> HealthResponse:
        return HealthResponse(status="ok", application=APPLICATION_NAME, version=__version__)

    def system_status(self) -> SystemStatusResponse:
        retrieval = self.approval.retrieval_approval()
        rag = self.approval.rag_approval()
        return SystemStatusResponse(
            application=APPLICATION_NAME,
            version=__version__,
            application_service_version=self.settings.milestone10.application_service_version,
            api_contract_version=self.settings.milestone10.api_contract_version,
            api_version=self.settings.milestone10.api_version,
            streamlit_demo_version=self.settings.milestone10.streamlit_demo_version,
            synthetic_data_only=self.settings.synthetic_data_only,
            clinical_use_prohibited=True,
            retrieval_approval_status=retrieval.approval_status,
            rag_approval_status=rag.approval_status,
            approved_retrieval_configuration=retrieval.configuration,
            generator_mode=self.evidence.manifest.generator_provider,
            operational_events_enabled=self.settings.milestone10.operational_events_enabled,
        )

    def ready(self) -> ReadinessResponse:
        checks: list[ReadinessCheck] = []
        checks.append(self._check("configuration", True, "configuration loaded"))
        checks.append(
            self._check("synthetic_only_mode", self.settings.synthetic_data_only, "synthetic only")
        )
        retrieval = self.approval.retrieval_approval()
        rag = self.approval.rag_approval()
        checks.append(
            self._check(
                "retrieval_approval",
                retrieval.approval_status.startswith("approved_for")
                and retrieval.approved_for_local_synthetic_demo,
                retrieval.approval_status,
            )
        )
        checks.append(
            self._check(
                "rag_approval",
                rag.approval_status == "approved_for_local_demo"
                and rag.approved_for_local_synthetic_demo,
                rag.approval_status,
            )
        )
        checks.append(
            self._check(
                "approved_retriever_config",
                self.evidence.manifest.retrieval_configuration_id == retrieval.configuration,
                self.evidence.manifest.retrieval_configuration_id,
            )
        )
        checks.append(
            self._check("prompt_assets", bool(self.evidence.answers), "prompt records available")
        )
        checks.append(
            self._check(
                "fixture_evidence", self.evidence.rag_run_dir.exists(), "canonical fixture readable"
            )
        )
        try:
            self.settings.milestone10.operational_event_root.mkdir(parents=True, exist_ok=True)
            writable = self.settings.milestone10.operational_event_root.is_dir()
        except OSError:
            writable = False
        checks.append(
            self._check("operational_output_directory", writable, "local portfolio evidence")
        )
        status = (
            "ready"
            if all(check.status == "passed" for check in checks if check.required)
            else "not_ready"
        )
        return ReadinessResponse(
            status=status,
            readiness_version=self.settings.milestone10.readiness_version,
            checks=checks,
            synthetic_data_only=self.settings.synthetic_data_only,
        )

    @staticmethod
    def _check(name: str, passed: bool, detail: str) -> ReadinessCheck:
        return ReadinessCheck(name=name, status="passed" if passed else "failed", detail=detail)
