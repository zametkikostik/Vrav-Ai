from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from core.modules.schemas.models import Envelope, EventType


class EventLog:
    """In-memory append-only event log indexed by session_id."""

    def __init__(self) -> None:
        self._events: Dict[str, List[Envelope]] = {}

    def append(self, envelope: Envelope) -> Envelope:
        self._events.setdefault(envelope.session_id, []).append(envelope)
        return envelope

    def replay(self, session_id: str, from_sequence: int = 1) -> List[Envelope]:
        return [e for e in self._events.get(session_id, []) if e.sequence_id >= from_sequence]

    def snapshot(self, path: str) -> None:
        data = {
            session_id: [asdict(event) for event in events]
            for session_id, events in self._events.items()
        }
        Path(path).write_text(json.dumps(data, default=str, ensure_ascii=False, indent=2), encoding="utf-8")

    def restore(self, path: str) -> int:
        source = Path(path)
        if not source.exists():
            return 0

        raw = json.loads(source.read_text(encoding="utf-8"))
        total = 0
        self._events = {}

        for session_id, events in raw.items():
            restored: List[Envelope] = []
            for event in events:
                restored.append(
                    Envelope(
                        event_type=EventType(event["event_type"]),
                        session_id=event["session_id"],
                        source=event["source"],
                        payload=event["payload"],
                        sequence_id=event["sequence_id"],
                        correlation_id=event.get("correlation_id"),
                        idempotency_key=event.get("idempotency_key"),
                        id=event.get("id"),
                        created_at=datetime.fromisoformat(event["created_at"]),
                    )
                )
                total += 1
            self._events[session_id] = restored

        return total


    def session_count(self, session_id: str) -> int:
        return len(self._events.get(session_id, []))
