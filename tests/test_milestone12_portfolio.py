from pathlib import Path

from healthcare_language_ai.portfolio.reports import (
    evidence_records,
    run_registry,
    validate_release_package,
    write_architecture_pack,
    write_evidence_index,
    write_milestone_audit,
    write_release_manifest,
    write_release_package,
    write_release_readiness,
    write_repository_audit,
    write_traceability,
)


def test_repository_and_milestone_audits_pass(tmp_path: Path) -> None:
    audit = write_repository_audit(tmp_path / "audit")
    milestones = write_milestone_audit(tmp_path / "milestones")

    assert audit["failed_items"] == 0
    assert audit["audit_reconciliation_status"] == "passed"
    assert milestones["milestones_audited"] == 11
    assert milestones["milestones_complete"] == 11
    assert milestones["overall_status"] == "passed"


def test_traceability_and_architecture_pack_are_complete(tmp_path: Path) -> None:
    traceability = write_traceability(tmp_path / "traceability")
    architecture = write_architecture_pack(tmp_path / "architecture")

    assert traceability["validation_status"] == "passed"
    assert traceability["requirements_missing"] == 0
    assert traceability["traceability_record_count"] >= 20
    assert architecture["architecture_document_count"] == 8
    assert architecture["diagram_count"] == 12
    assert architecture["validation_status"] == "passed"


def test_evidence_index_uses_existing_artifacts_only(tmp_path: Path) -> None:
    records = evidence_records()
    payload = write_evidence_index(tmp_path)

    assert all(record.status == "passed" for record in records)
    assert all(record.evidence_id != "EV-RELEASE" for record in records)
    assert payload["validation_status"] == "passed"
    assert payload["evidence_count"] == len(records)


def test_run_registry_records_key_approval_ids() -> None:
    registry = run_registry()

    assert registry.synthetic_dataset_id == "synthetic_clinical_documents"
    assert registry.retrieval_approval_id.startswith("RETAPP-")
    assert registry.rag_approval_status == "approved_for_local_demo"
    assert registry.portfolio_assurance_id == "ASSURE-9b83e5cbd4ef84cfb0eb3e45"


def test_release_readiness_manifest_and_package_pass(tmp_path: Path) -> None:
    release_dir = tmp_path / "release"
    package_root = tmp_path / "package"

    readiness = write_release_readiness(release_dir, "2026-01-19T09:00:00+00:00")
    manifest = write_release_manifest(release_dir, release_dir, "2026-01-20T09:00:00+00:00")
    package = write_release_package(release_dir, package_root, "2026-01-20T09:00:00+00:00")
    validation = validate_release_package(Path(package.package_output_path))

    assert readiness.ready_for_portfolio_release is True
    assert readiness.production_ready is False
    assert readiness.clinically_validated is False
    assert manifest.production_ready is False
    assert manifest.clinically_validated is False
    assert package.release_id == manifest.release_id
    assert validation["package_validation_status"] == "passed"
