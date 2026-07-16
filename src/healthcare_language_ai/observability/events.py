"""Operational event helpers."""

from __future__ import annotations

import hashlib
import uuid

from healthcare_language_ai import __version__
from healthcare_language_ai.observability.contracts import OperationalEvent


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_event(
    *,
    event_type: str,
    request_id: str,
    query_text: str = "",
    query_category: str = "",
    retrieval_status: str = "",
    answer_status: str = "",
    citation_status: str = "",
    groundedness_status: str = "",
    safety_status: str = "",
    error_code: str = "",
    duration_ms: float = 0.0,
) -> OperationalEvent:
    return OperationalEvent(
        event_id=f"OP-{uuid.uuid4().hex}",
        event_type=event_type,
        request_id=request_id,
        query_checksum=checksum_text(query_text) if query_text else "",
        query_category=query_category,
        retrieval_status=retrieval_status,
        answer_status=answer_status,
        citation_status=citation_status,
        groundedness_status=groundedness_status,
        safety_status=safety_status,
        error_code=error_code,
        duration_ms=duration_ms,
        application_version=__version__,
    )
