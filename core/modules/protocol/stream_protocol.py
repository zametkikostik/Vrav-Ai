from __future__ import annotations

import json
from dataclasses import asdict
from typing import Iterator

from core.modules.schemas.models import Envelope


class StreamProtocol:
    """SSE-compatible protocol with UTF-8 JSON envelopes and monotonic event IDs."""

    @staticmethod
    def encode(envelope: Envelope) -> bytes:
        body = json.dumps(asdict(envelope), default=str, ensure_ascii=False)
        wire = (
            f"event: {envelope.event_type.value}\n"
            f"id: {envelope.sequence_id}\n"
            f"data: {body}\n\n"
        )
        return wire.encode("utf-8")

    @staticmethod
    def decode(stream: str) -> Iterator[Envelope]:
        current: dict[str, str] = {}
        for line in stream.splitlines():
            if not line.strip():
                if "data" in current:
                    data = json.loads(current["data"])
                    yield Envelope(**data)
                current = {}
                continue

            key, _, value = line.partition(":")
            current[key.strip()] = value.strip()


class StreamBuffer:
    """Collects encoded frames and can return a replay-safe stream dump."""

    def __init__(self) -> None:
        self._frames: list[bytes] = []

    def push(self, envelope: Envelope) -> None:
        self._frames.append(StreamProtocol.encode(envelope))

    def dump(self) -> bytes:
        return b"".join(self._frames)

    def clear(self) -> None:
        self._frames.clear()
