"""Deterministic local backup tooling for selected portfolio evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from healthcare_language_ai.assurance.contracts import BackupManifest
from healthcare_language_ai.assurance.inventory import checksum_data, checksum_text

BACKUP_SELECTIONS = [
    Path("config/application.yaml"),
    Path("schemas/api/query-request.schema.json"),
    Path("schemas/api/query-response.schema.json"),
    Path("tests/fixtures/api/openapi.json"),
    Path("tests/fixtures/api/routes.json"),
    Path("tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874/rag_manifest.json"),
    Path(
        "tests/fixtures/rag/evaluation/RAGEVAL-d8d3b3b6892133372f91d017/rag_approval_decision.json"
    ),
    Path(
        "tests/fixtures/retrieval-remediation/comparison/REMCOMP-1a3a8c86fc4567de3049f352/retrieval_approval_decision.json"
    ),
    Path("tests/fixtures/demo/DEMO-7d8d73b2b21ec496c6e47175/demo-session.json"),
    Path("reports/portfolio/platform-evidence-summary.md"),
]


def selected_backup_files(profile: str) -> list[Path]:
    if profile != "portfolio-critical":
        msg = "only portfolio-critical backup profile is supported"
        raise ValueError(msg)
    return [path for path in BACKUP_SELECTIONS if path.exists()]


def create_backup(profile: str, output_root: Path) -> BackupManifest:
    files = selected_backup_files(profile)
    checksums = {path.as_posix(): checksum_text(path.read_text(encoding="utf-8")) for path in files}
    backup_id = "BACKUP-" + checksum_data({"profile": profile, "files": checksums})[:24]
    backup_dir = output_root / backup_id
    files_dir = backup_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        destination = files_dir / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    manifest = BackupManifest(
        backup_id=backup_id,
        profile=profile,
        selected_file_count=len(files),
        files=checksums,
        checksum=checksum_data(checksums),
    )
    (backup_dir / "backup-manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (backup_dir / "checksum-manifest.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (backup_dir / "README.md").write_text(
        "# Assurance Backup\n\nDeterministic selected local portfolio evidence backup.\n",
        encoding="utf-8",
    )
    return manifest


def validate_backup(backup_dir: Path) -> list[str]:
    failures: list[str] = []
    manifest = BackupManifest.model_validate_json((backup_dir / "backup-manifest.json").read_text())
    for relative, expected in manifest.files.items():
        path = backup_dir / "files" / relative
        if not path.exists():
            failures.append(f"missing {relative}")
            continue
        if checksum_text(path.read_text(encoding="utf-8")) != expected:
            failures.append(f"checksum mismatch {relative}")
    return failures
