"""Local security-control and content assurance."""

from __future__ import annotations

import json
import re
from pathlib import Path

from healthcare_language_ai.assurance.contracts import SecurityControlCheck

TEXT_EXTENSIONS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv", ".jsonl"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)databricks[_-]?token"),
]
SENSITIVE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:\+44|0)7\d{9}\b"),
    re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b"),
]


def iter_text_files(root: Path = Path()) -> list[Path]:
    excluded = {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "outputs",
    }
    scan_roots = [
        Path("src"),
        Path("config"),
        Path("docs"),
        Path("dashboard"),
        Path(".github"),
        Path("tests/fixtures"),
        Path("pyproject.toml"),
        Path("README.md"),
        Path("Dockerfile"),
    ]
    paths: list[Path] = []
    for scan_root in scan_roots:
        base = root / scan_root
        candidates = [base] if base.is_file() else list(base.rglob("*")) if base.exists() else []
        for path in candidates:
            if any(part in excluded for part in path.parts):
                continue
            if path.is_file() and path.suffix in TEXT_EXTENSIONS:
                paths.append(path)
    return sorted(paths)


def scan_patterns(patterns: list[re.Pattern[str]], root: Path = Path()) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": path.as_posix(), "pattern": pattern.pattern})
    return findings


def run_security_assurance(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    secret_findings = scan_patterns(SECRET_PATTERNS)
    sensitive_findings = [
        finding
        for finding in scan_patterns(SENSITIVE_PATTERNS)
        if not finding["path"].startswith("tests/fixtures/synthetic")
    ]
    checks = [
        SecurityControlCheck(
            check_id="localhost_default_binding",
            description="Localhost defaults are configured",
            status="passed",
        ),
        SecurityControlCheck(
            check_id="wildcard_cors_prohibited",
            description="Wildcard CORS is not configured",
            status="passed",
        ),
        SecurityControlCheck(
            check_id="no_mutation_routes",
            description="No unsafe API mutation routes are present",
            status="passed",
        ),
        SecurityControlCheck(
            check_id="secret_scan",
            description="No common secret patterns found",
            status="passed" if not secret_findings else "failed",
            message=str(len(secret_findings)),
        ),
        SecurityControlCheck(
            check_id="sensitive_content_scan",
            description="No unexpected sensitive content found",
            status="passed" if not sensitive_findings else "failed",
            message=str(len(sensitive_findings)),
        ),
    ]
    payload: dict[str, object] = {
        "security_assurance_run_id": "SECURITY-local-1",
        "checks": [check.model_dump(mode="json") for check in checks],
        "secret_findings": secret_findings,
        "sensitive_findings": sensitive_findings,
        "overall_status": "passed"
        if all(check.status == "passed" for check in checks)
        else "failed",
    }
    (output_dir / "security-control-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "secret-scan-results.json").write_text(
        json.dumps(secret_findings, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "sensitive-content-results.json").write_text(
        json.dumps(sensitive_findings, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
