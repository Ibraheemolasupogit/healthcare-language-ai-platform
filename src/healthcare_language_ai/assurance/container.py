"""Static Dockerfile assurance checks."""

from __future__ import annotations

import json
from pathlib import Path

from healthcare_language_ai.assurance.contracts import ContainerAssuranceCheck


def run_container_assurance(dockerfile: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    text = dockerfile.read_text(encoding="utf-8")
    checks = [
        ContainerAssuranceCheck(
            check_id="python_slim_base",
            status="passed" if "FROM python:3.12-slim" in text else "failed",
            message="Pinned Python slim base family",
        ),
        ContainerAssuranceCheck(
            check_id="non_root_user",
            status="passed" if "USER app" in text else "failed",
            message="Non-root runtime user configured",
        ),
        ContainerAssuranceCheck(
            check_id="writable_outputs",
            status="passed" if "mkdir -p data outputs reports" in text else "failed",
            message="Writable local output directories configured",
        ),
        ContainerAssuranceCheck(
            check_id="model_free",
            status="passed"
            if "sentence-transformers" not in text and "torch" not in text
            else "failed",
            message="Default image remains model-free",
        ),
        ContainerAssuranceCheck(
            check_id="credential_free",
            status="passed"
            if "SECRET" not in text.upper() and "TOKEN" not in text.upper()
            else "failed",
            message="No embedded credentials detected",
        ),
    ]
    payload: dict[str, object] = {
        "container_assurance_version": "1.0.0",
        "checks": [check.model_dump(mode="json") for check in checks],
        "overall_status": "passed"
        if all(check.status == "passed" for check in checks)
        else "failed",
    }
    (output_dir / "container-assurance.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
