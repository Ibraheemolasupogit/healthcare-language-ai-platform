"""Reusable Streamlit helpers for the local portfolio dashboard."""

from __future__ import annotations

from healthcare_language_ai.application.contracts import DISCLAIMER
from healthcare_language_ai.application.dependencies import build_services


def safety_banner_text() -> str:
    return DISCLAIMER


def acknowledgement_required(acknowledged: bool) -> bool:
    return acknowledged


def get_services():
    return build_services()


def render_banner(st_module) -> None:
    st_module.warning(safety_banner_text())
