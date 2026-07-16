"""Validation helpers for safe local operational event files."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.observability.contracts import OperationalEvent


def validate_event_dir(events_dir: Path) -> list[str]:
    failures: list[str] = []
    if not events_dir.exists():
        return failures
    for path in events_dir.glob("*.jsonl"):
        raw = path.read_bytes()
        if b"\r\n" in raw:
            failures.append(f"{path.name} must use LF endings")
        for line in raw.decode("utf-8").splitlines():
            event = OperationalEvent.model_validate_json(line)
            payload = event.model_dump_json().lower()
            for forbidden in ("query_text", "answer_text", "evidence_text", "document_text"):
                if forbidden in payload:
                    failures.append(f"{path.name} contains forbidden field {forbidden}")
    return failures
