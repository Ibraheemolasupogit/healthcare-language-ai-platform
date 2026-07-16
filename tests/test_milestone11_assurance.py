import json
from pathlib import Path

import pytest

from healthcare_language_ai.api.rate_limit import LocalRateLimiter
from healthcare_language_ai.assurance.backup import create_backup, validate_backup
from healthcare_language_ai.assurance.compatibility import compare_contracts
from healthcare_language_ai.assurance.configuration import validate_configuration_assurance
from healthcare_language_ai.assurance.container import run_container_assurance
from healthcare_language_ai.assurance.dependencies import build_dependency_inventory, write_sbom
from healthcare_language_ai.assurance.inventory import (
    build_baseline,
    generate_contract_inventory,
    write_contract_inventory,
)
from healthcare_language_ai.assurance.recovery import restore_backup, run_recovery_exercise
from healthcare_language_ai.assurance.reports import generate_portfolio_assurance
from healthcare_language_ai.assurance.security import run_security_assurance, scan_patterns
from healthcare_language_ai.config import AppSettings, Milestone10Settings, Milestone11Settings
from healthcare_language_ai.observability.integrity import validate_operational_integrity


def test_contract_inventory_is_deterministic_and_unique() -> None:
    first = generate_contract_inventory()
    second = generate_contract_inventory()
    assert [item.model_dump() for item in first] == [item.model_dump() for item in second]
    assert len({item.contract_id for item in first}) == len(first)
    assert any(item.contract_type == "api_route" for item in first)
    assert any(item.contract_type == "cli_command" for item in first)
    assert any(item.contract_type == "prompt_contract" for item in first)


def test_contract_baseline_and_no_change_comparison_pass(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    write_contract_inventory(baseline_dir)
    report = compare_contracts(baseline_dir, tmp_path / "compatibility")
    assert report.breaking_change_count == 0
    assert report.overall_compatibility_status == "passed"


def test_removed_route_is_breaking(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    write_contract_inventory(baseline_dir)
    records = json.loads((baseline_dir / "contract-inventory.json").read_text())
    records.append(
        {
            "contract_id": "api_route:/removed",
            "contract_type": "api_route",
            "contract_version": "1.0.0",
            "location": "api.openapi",
            "owner_module": "api.openapi",
            "stability": "stable",
            "compatibility_policy": "stable_contract_v1",
            "introduced_milestone": "M11",
            "deprecated": False,
            "replacement_contract_id": "",
            "checksum": "removed",
        }
    )
    (baseline_dir / "contract-inventory.json").write_text(json.dumps(records))
    report = compare_contracts(baseline_dir, tmp_path / "compatibility")
    assert report.breaking_change_count == 1
    assert report.api_breaking_change_count == 1


def test_configuration_hardening_rejects_unsafe_values() -> None:
    safe = AppSettings()
    assert all(row["status"] == "passed" for row in validate_configuration_assurance(safe))
    unsafe = AppSettings(
        milestone10=Milestone10Settings(cors_enabled=True, allowed_origins=["*"]),
        milestone11=Milestone11Settings(),
    )
    assert any(
        row["check_id"] == "wildcard_cors_rejected" and row["status"] == "failed"
        for row in validate_configuration_assurance(unsafe)
    )


def test_rate_limiter_allows_rejects_and_isolates_clients() -> None:
    limiter = LocalRateLimiter(requests=2, window_seconds=60)
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")


def test_operational_integrity_accepts_fixture_and_quarantines_malformed(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "bad.jsonl").write_text('{"not": "valid"}\n', encoding="utf-8")
    result = validate_operational_integrity(events_dir, tmp_path / "out", tmp_path / "quarantine")
    assert result["rejected_event_count"] == 1
    assert result["overall_status"] == "failed"
    fixture = validate_operational_integrity(
        Path("tests/fixtures/observability"), tmp_path / "fixture-out", tmp_path / "fixture-q"
    )
    assert fixture["overall_status"] == "passed"


def test_backup_restore_and_recovery_exercise(tmp_path: Path) -> None:
    manifest = create_backup("portfolio-critical", tmp_path / "backups")
    backup_dir = tmp_path / "backups" / manifest.backup_id
    assert validate_backup(backup_dir) == []
    restore = restore_backup(backup_dir, tmp_path / "restored")
    assert restore.checksum_status == "passed"
    exercise = run_recovery_exercise("portfolio-critical", tmp_path / "recovery")
    assert exercise.recovery_exercise_status == "passed"


def test_security_dependency_sbom_container_and_portfolio_reports(tmp_path: Path) -> None:
    security = run_security_assurance(tmp_path)
    assert security["overall_status"] == "passed"
    assert scan_patterns([], Path()) == []
    inventory = build_dependency_inventory()
    assert any(record.package_name.lower() == "fastapi" for record in inventory.records)
    assert any(record.package_name.lower() == "streamlit" for record in inventory.records)
    assert not inventory.policy_violations
    sbom = write_sbom(tmp_path)
    assert sbom.vulnerability_status == "not_evaluated_offline_inventory_only"
    container = run_container_assurance(Path("Dockerfile"), tmp_path)
    assert container["overall_status"] == "passed"
    baseline_dir = tmp_path / "baseline"
    write_contract_inventory(baseline_dir)
    settings = AppSettings(milestone11=Milestone11Settings(contract_baseline_root=baseline_dir))
    decision = generate_portfolio_assurance(settings, tmp_path / "assurance")
    assert decision.portfolio_readiness_status == "ready_for_local_portfolio_demonstration"
    assert not decision.production_ready
    assert not decision.clinically_ready


def test_checked_in_assurance_fixtures_validate() -> None:
    baseline = build_baseline(generate_contract_inventory())
    fixture = json.loads(
        Path("tests/fixtures/assurance/contracts/baseline/baseline-manifest.json").read_text()
    )
    assert fixture["baseline_id"] == baseline.baseline_id
    assert Path("tests/fixtures/assurance/runtime-smoke/smoke-contract.json").exists()
    assert Path("tests/fixtures/assurance/security/security-control-results.json").exists()


def test_restore_requires_destination_guard(tmp_path: Path) -> None:
    manifest = create_backup("portfolio-critical", tmp_path / "backups")
    with pytest.raises(ValueError):
        restore_backup(tmp_path / "backups" / manifest.backup_id, Path.cwd())
