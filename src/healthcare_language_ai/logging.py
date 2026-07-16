"""Structured logging helpers with content-safe defaults."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from healthcare_language_ai.config import AppSettings

SENSITIVE_KEYS = {"text", "clinical_text", "secret", "token", "password", "api_key"}


def _redact_sensitive_fields(
    _logger: logging.Logger, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(settings: AppSettings) -> None:
    """Configure structlog for local console or JSON logs."""
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _redact_sensitive_fields,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    renderer: Any
    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)
    processors.append(renderer)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
        force=True,
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.log_level)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )


def bind_log_context(
    *, run_id: str | None = None, document_id: str | None = None, pipeline_stage: str | None = None
) -> None:
    """Bind safe correlation fields for subsequent log events."""
    context = {
        key: value
        for key, value in {
            "run_id": run_id,
            "document_id": document_id,
            "pipeline_stage": pipeline_stage,
        }.items()
        if value is not None
    }
    structlog.contextvars.bind_contextvars(**context)
