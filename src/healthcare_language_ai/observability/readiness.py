"""Readiness snapshot helpers."""

from healthcare_language_ai.application.contracts import ReadinessResponse
from healthcare_language_ai.observability.contracts import ReadinessSnapshot


def snapshot_from_readiness(readiness: ReadinessResponse) -> ReadinessSnapshot:
    return ReadinessSnapshot(
        status=readiness.status,
        passed_checks=sum(check.status == "passed" for check in readiness.checks),
        failed_checks=sum(check.status == "failed" for check in readiness.checks),
    )
