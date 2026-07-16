"""Portfolio assurance report generation."""

from __future__ import annotations

import json
from pathlib import Path

from healthcare_language_ai.assurance.compatibility import compare_contracts
from healthcare_language_ai.assurance.configuration import write_configuration_assurance
from healthcare_language_ai.assurance.container import run_container_assurance
from healthcare_language_ai.assurance.contracts import (
    AssuranceGateResult,
    PortfolioAssuranceDecision,
)
from healthcare_language_ai.assurance.dependencies import write_dependency_inventory, write_sbom
from healthcare_language_ai.assurance.inventory import checksum_data
from healthcare_language_ai.assurance.recovery import run_recovery_exercise
from healthcare_language_ai.assurance.security import run_security_assurance
from healthcare_language_ai.config import AppSettings
from healthcare_language_ai.observability.integrity import validate_operational_integrity


def generate_portfolio_assurance(
    settings: AppSettings, output_dir: Path
) -> PortfolioAssuranceDecision:
    output_dir.mkdir(parents=True, exist_ok=True)
    compatibility = compare_contracts(settings.milestone11.contract_baseline_root, output_dir)
    config_checks = write_configuration_assurance(settings, output_dir)
    integrity = validate_operational_integrity(
        Path("tests/fixtures/observability"),
        output_dir,
        settings.milestone11.operational_event_quarantine_root,
    )
    recovery = run_recovery_exercise("portfolio-critical", Path("outputs/assurance/recovery"))
    security = run_security_assurance(output_dir)
    dependencies = write_dependency_inventory(output_dir)
    sbom = write_sbom(output_dir)
    container = run_container_assurance(Path("Dockerfile"), output_dir)
    configuration_passed = all(row["status"] == "passed" for row in config_checks)
    gates = [
        AssuranceGateResult(
            gate_id="contract_compatibility",
            required=True,
            status="passed" if compatibility.overall_compatibility_status == "passed" else "failed",
            evidence=compatibility.compatibility_run_id,
        ),
        AssuranceGateResult(
            gate_id="configuration_safety",
            required=True,
            status="passed" if configuration_passed else "failed",
            evidence="configuration-assurance.json",
        ),
        AssuranceGateResult(
            gate_id="operational_integrity",
            required=True,
            status="passed" if integrity["overall_status"] == "passed" else "failed",
            evidence="operational-integrity.json",
        ),
        AssuranceGateResult(
            gate_id="backup_recovery",
            required=True,
            status="passed" if recovery.recovery_exercise_status == "passed" else "failed",
            evidence=recovery.recovery_run_id,
        ),
        AssuranceGateResult(
            gate_id="security_assurance",
            required=True,
            status="passed" if security["overall_status"] == "passed" else "failed",
            evidence="security-control-report.json",
        ),
        AssuranceGateResult(
            gate_id="dependency_policy",
            required=True,
            status="passed" if not dependencies.policy_violations else "failed",
            evidence=dependencies.dependency_inventory_id,
        ),
        AssuranceGateResult(
            gate_id="sbom",
            required=True,
            status="passed" if sbom.components else "failed",
            evidence=sbom.sbom_id,
        ),
        AssuranceGateResult(
            gate_id="container_static_assurance",
            required=True,
            status="passed" if container["overall_status"] == "passed" else "failed",
            evidence="container-assurance.json",
        ),
        AssuranceGateResult(
            gate_id="runtime_smoke",
            required=False,
            status="conditional",
            evidence="runtime smoke is explicit, bounded, and not required by make validate",
        ),
    ]
    failed_required = [gate for gate in gates if gate.required and gate.status != "passed"]
    runtime_smoke_conditional = any(gate.status == "conditional" for gate in gates)
    status = "ready_for_local_portfolio_demonstration" if not failed_required else "not_ready"
    decision = PortfolioAssuranceDecision(
        assurance_run_id="ASSURE-" + checksum_data([gate.model_dump() for gate in gates])[:24],
        required_gate_count=sum(gate.required for gate in gates),
        passed_required_gates=sum(gate.required and gate.status == "passed" for gate in gates),
        failed_required_gates=len(failed_required),
        conditional_gate_count=sum(gate.status == "conditional" for gate in gates),
        portfolio_readiness_status=status,
        ready_for_local_portfolio_demonstration=status == "ready_for_local_portfolio_demonstration",
        known_blocked_checks=[],
        known_degraded_components=["runtime_smoke"] if runtime_smoke_conditional else [],
        gates=gates,
    )
    (output_dir / "readiness-assurance.json").write_text(
        json.dumps(
            {"gates": [gate.model_dump(mode="json") for gate in gates]},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "portfolio-assurance-summary.md").write_text(
        "\n".join(
            [
                "# Portfolio Assurance Summary",
                "",
                f"Assurance run ID: {decision.assurance_run_id}",
                f"Status: {decision.portfolio_readiness_status}",
                "Production ready: no",
                "Clinically ready: no",
                "Cloud deployment approved: no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "runtime-smoke-summary.json").write_text(
        json.dumps(
            {"status": "not_run_by_portfolio_assurance", "browser_interaction": False},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "portfolio-assurance-decision.json").write_text(
        decision.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return decision
