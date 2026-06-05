from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    CORE = "core"


class EventType(str, Enum):
    SESSION_STARTED = "session.started"
    USER_MESSAGE = "message.user"
    AGENT_PLAN = "agent.plan"
    AGENT_THOUGHT = "agent.thought"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    RESPONSE_CHUNK = "response.chunk"
    RESPONSE_COMPLETED = "response.completed"
    ERROR = "error"


@dataclass(slots=True)
class Message:
    role: Role
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class Envelope:
    event_type: EventType
    session_id: str
    source: str
    payload: Dict[str, Any]
    sequence_id: int
    correlation_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SessionState:
    session_id: str
    messages: List[Message] = field(default_factory=list)
    last_sequence: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def append(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
