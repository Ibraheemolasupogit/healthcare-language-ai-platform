"""Shared assurance gate helpers."""

from __future__ import annotations

from healthcare_language_ai.assurance.contracts import AssuranceGateResult


def required_gate(gate_id: str, passed: bool, evidence: str) -> AssuranceGateResult:
    return AssuranceGateResult(
        gate_id=gate_id,
        required=True,
        status="passed" if passed else "failed",
        evidence=evidence,
    )


def conditional_gate(gate_id: str, evidence: str) -> AssuranceGateResult:
    return AssuranceGateResult(
        gate_id=gate_id,
        required=False,
        status="conditional",
        evidence=evidence,
    )
