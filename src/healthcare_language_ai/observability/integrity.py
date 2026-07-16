"""Operational event integrity validation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from healthcare_language_ai.assurance.contracts import (
    MalformedEventRecord,
    OperationalEventManifest,
)
from healthcare_language_ai.observability.contracts import OperationalEvent


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_operational_integrity(
    events_dir: Path, output_dir: Path, quarantine_root: Path
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    quarantine_root.mkdir(parents=True, exist_ok=True)
    manifests: list[OperationalEventManifest] = []
    malformed: list[MalformedEventRecord] = []
    seen: set[str] = set()
    duplicates = 0
    accepted = 0
    unknown_version = 0
    for event_file in sorted(events_dir.glob("*.jsonl")) if events_dir.exists() else []:
        sequence_start = accepted + 1
        lines = event_file.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            try:
                event = OperationalEvent.model_validate_json(line)
            except ValueError:
                qpath = quarantine_root / f"{event_file.stem}-{line_number}.json"
                qpath.write_text(json.dumps({"line": line}) + "\n", encoding="utf-8")
                malformed.append(
                    MalformedEventRecord(
                        source_file=event_file.as_posix(),
                        line_number=line_number,
                        reason="schema_validation_failed",
                        quarantined_path=qpath.as_posix(),
                    )
                )
                continue
            if event.event_id in seen:
                duplicates += 1
                continue
            seen.add(event.event_id)
            accepted += 1
            if event.operational_event_version != "1.0.0":
                unknown_version += 1
        manifests.append(
            OperationalEventManifest(
                event_file=event_file.as_posix(),
                sequence_start=sequence_start,
                sequence_end=accepted,
                event_count=max(0, accepted - sequence_start + 1),
                file_size=event_file.stat().st_size,
                checksum=file_checksum(event_file),
                created_at=datetime.fromtimestamp(event_file.stat().st_mtime, UTC),
                closed_at=datetime.fromtimestamp(event_file.stat().st_mtime, UTC),
            )
        )
    payload: dict[str, object] = {
        "operational_integrity_version": "1.0.0",
        "accepted_event_count": accepted,
        "rejected_event_count": len(malformed),
        "duplicate_event_count": duplicates,
        "unknown_version_count": unknown_version,
        "manifests": [item.model_dump(mode="json") for item in manifests],
        "malformed_events": [item.model_dump(mode="json") for item in malformed],
        "overall_status": "passed" if not malformed and duplicates == 0 else "failed",
    }
    (output_dir / "operational-integrity.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
