"""Local graceful-degradation helpers."""

from __future__ import annotations

from healthcare_language_ai.assurance.contracts import ComponentReadiness


def component_status(
    component: str, passed: bool, required: bool, message: str
) -> ComponentReadiness:
    if passed:
        status = "healthy"
    else:
        status = "unavailable" if required else "degraded"
    return ComponentReadiness(
        component=component, status=status, required=required, message=message
    )
