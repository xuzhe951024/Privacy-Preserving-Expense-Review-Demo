from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models import AuditEvent
from src.report_writer import write_jsonl


class AuditLogger:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, stage: str, action: str, **details: Any) -> None:
        self._events.append(
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage=stage,
                action=action,
                details=details,
            )
        )

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]

    def write_jsonl(self, path: str | Path) -> Path:
        return write_jsonl(path, self.to_list())

