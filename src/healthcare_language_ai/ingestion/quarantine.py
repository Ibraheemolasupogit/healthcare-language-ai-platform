"""Quarantine evidence helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from healthcare_language_ai.ingestion.contracts import QuarantineRecord
from healthcare_language_ai.synthetic.serialization import write_json, write_jsonl
from healthcare_language_ai.utils.identifiers import deterministic_id


def quarantine_record(
    *,
    source_file: str,
    source_line_number: int | None,
    record_identifier: str | None,
    error_code: str,
    error_category: str,
    message: str,
    payload: object,
    timestamp: datetime,
) -> QuarantineRecord:
    return QuarantineRecord(
        source_file=source_file,
        source_line_number=source_line_number,
        record_identifier=record_identifier,
        error_code=error_code,
        error_category=error_category,
        sanitised_error_message=message,
        payload_checksum=deterministic_id(str(payload), length=64),
        quarantine_timestamp=timestamp,
    )


def write_quarantine(output_dir: Path, records: list[QuarantineRecord]) -> None:
    quarantine_dir = output_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(quarantine_dir / "quarantine_records.jsonl", list(records))
    write_json(
        quarantine_dir / "quarantine_summary.json",
        {
            "quarantine_count": len(records),
            "payload_checksums": [record.payload_checksum for record in records],
            "contains_full_clinical_text": False,
        },
    )
