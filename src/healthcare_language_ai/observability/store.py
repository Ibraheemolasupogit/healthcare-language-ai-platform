"""Append-only local JSONL event store with small-file rotation."""

from __future__ import annotations

from pathlib import Path

from healthcare_language_ai.observability.contracts import OperationalEvent


class EventStore:
    def __init__(
        self, root: Path, max_bytes: int, retention_files: int, enabled: bool = True
    ) -> None:
        self.root = root
        self.max_bytes = max_bytes
        self.retention_files = retention_files
        self.enabled = enabled

    @property
    def current_path(self) -> Path:
        return self.root / "operational-events.jsonl"

    def append(self, event: OperationalEvent) -> None:
        if not self.enabled:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        with self.current_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(event.model_dump_json() + "\n")

    def read_events(self) -> list[OperationalEvent]:
        if not self.root.exists():
            return []
        events: list[OperationalEvent] = []
        for path in sorted(self.root.glob("*.jsonl")):
            with path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        events.append(OperationalEvent.model_validate_json(line))
                    except ValueError:
                        continue
        return events

    def _rotate_if_needed(self) -> None:
        path = self.current_path
        if not path.exists() or path.stat().st_size < self.max_bytes:
            return
        rotated = (
            self.root
            / f"operational-events-{len(list(self.root.glob('operational-events-*'))) + 1}.jsonl"
        )
        path.replace(rotated)
        rotated_files = sorted(
            self.root.glob("operational-events-*.jsonl"), key=lambda item: item.stat().st_mtime
        )
        for old in rotated_files[: -self.retention_files]:
            old.unlink()
