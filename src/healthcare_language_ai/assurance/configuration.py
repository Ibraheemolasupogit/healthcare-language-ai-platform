"""Configuration hardening checks."""

from __future__ import annotations

import json
from pathlib import Path

from healthcare_language_ai.config import AppSettings


def validate_configuration_assurance(settings: AppSettings) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    def add(name: str, passed: bool, message: str) -> None:
        checks.append(
            {"check_id": name, "status": "passed" if passed else "failed", "message": message}
        )

    m10 = settings.milestone10
    m11 = settings.milestone11
    public_bind = m10.api_host == "0.0.0.0" or m10.streamlit_host == "0.0.0.0"
    add(
        "localhost_default_binding",
        not public_bind or m11.allow_unsafe_local_binding,
        "localhost binding",
    )
    add(
        "wildcard_cors_rejected",
        "*" not in m10.allowed_origins and not m10.cors_enabled,
        "CORS safe",
    )
    add(
        "positive_timeouts",
        m11.query_timeout_seconds > 0 and m11.trace_timeout_seconds > 0,
        "timeouts",
    )
    add("positive_concurrency", m11.maximum_concurrent_queries > 0, "concurrency")
    add(
        "rate_limit_safe",
        m11.rate_limit_requests > 0 and m11.rate_limit_window_seconds > 0,
        "rate limit",
    )
    add(
        "event_root_local",
        not m10.operational_event_root.is_absolute(),
        "operational event root remains repository-relative",
    )
    add(
        "unsafe_override_default_false",
        not m11.allow_unsafe_local_binding,
        "unsafe override disabled",
    )
    return checks


def write_configuration_assurance(settings: AppSettings, output_dir: Path) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = validate_configuration_assurance(settings)
    payload = {
        "configuration_assurance_version": settings.milestone11.configuration_assurance_version,
        "checks": checks,
        "overall_status": "passed"
        if all(row["status"] == "passed" for row in checks)
        else "failed",
    }
    (output_dir / "configuration-assurance.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return checks
