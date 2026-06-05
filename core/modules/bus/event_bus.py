from __future__ import annotations

from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List

from core.modules.schemas.models import Envelope, EventType

EventHandler = Callable[[Envelope], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[EventType, List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, envelope: Envelope) -> None:
        for handler in self._subscribers.get(envelope.event_type, []):
            handler(envelope)

    def stats(self) -> Dict[str, int]:
        return {event_type.value: len(handlers) for event_type, handlers in self._subscribers.items()}
