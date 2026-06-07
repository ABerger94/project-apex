from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from apex.core.models import MemoryEvent


class EventMemory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event_type: str, data: dict) -> MemoryEvent:
        event = MemoryEvent(event_type=event_type, data=data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        return event

    def read_recent(self, limit: int = 20) -> tuple[MemoryEvent, ...]:
        if not self.path.exists():
            return ()
        events: list[MemoryEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines()[-limit:]:
            if not line.strip():
                continue
            data = json.loads(line)
            events.append(MemoryEvent(
                event_type=str(data["event_type"]),
                data=dict(data.get("data") or {}),
                timestamp=str(data["timestamp"]),
            ))
        return tuple(events)

