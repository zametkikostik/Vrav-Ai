from __future__ import annotations

from dataclasses import asdict
from threading import RLock
from typing import Iterable, List, Tuple

from core.modules.agent.runtime import AgentRuntime
from core.modules.agent.toolkit import ToolRegistry, ToolSpec
from core.modules.bus.event_bus import EventBus
from core.modules.protocol.stream_protocol import StreamBuffer
from core.modules.registry.event_log import EventLog
from core.modules.registry.rate_limiter import RateLimiter
from core.modules.registry.session_store import SessionStore
from core.modules.schemas.models import Envelope, EventType, Message, Role
from core.modules.schemas.validators import ValidationError, validate_user_message
from core.modules.streaming.chunker import chunk_text


class VravEngine:
    """Core orchestrator for VRAV AI: user input -> agent runtime -> streamed response events."""

    def __init__(self) -> None:
        self.bus = EventBus()
        self.sessions = SessionStore()
        self.agent = AgentRuntime()
        self.tools = ToolRegistry()
        self.event_log = EventLog()
        self.rate_limiter = RateLimiter(max_requests=50, window_seconds=60)
        self._state_lock = RLock()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.tools.register(ToolSpec(name="echo", description="Echo raw input", fn=lambda arg: arg))
        self.tools.register(ToolSpec(name="upper", description="Uppercase string", fn=lambda arg: arg.upper()))

    def _emit(self, envelope: Envelope) -> None:
        persisted = self.event_log.append(envelope)
        self.bus.publish(persisted)

    def _parse_tool_command(self, content: str) -> Tuple[str, str] | None:
        if not content.startswith("/tool "):
            return None
        _, _, tail = content.partition("/tool ")
        tool_name, _, arg = tail.partition(" ")
        return tool_name.strip(), arg.strip()

    def ingest_user_message(self, session_id: str, text: str) -> List[Envelope]:
        """Process one message atomically to preserve per-session ordering."""
        with self._state_lock:
            return self._ingest_user_message(session_id, text)

    def _ingest_user_message(self, session_id: str, text: str) -> List[Envelope]:
        state = self.sessions.get_or_create(session_id)
        user_message = Message(role=Role.USER, content=text)

        def next_seq() -> int:
            state.last_sequence += 1
            return state.last_sequence

        if not self.rate_limiter.allow(session_id):
            error = Envelope(
                event_type=EventType.ERROR,
                session_id=session_id,
                source="core.engine",
                payload={"error": "rate_limited", "message_id": user_message.id},
                sequence_id=next_seq(),
                correlation_id=user_message.id,
            )
            self._emit(error)
            return [error]

        envelopes: List[Envelope] = []

        try:
            validate_user_message(user_message)
            state.append(user_message)
            envelopes.append(Envelope(EventType.USER_MESSAGE, session_id, "core.engine", asdict(user_message), next_seq()))

            plan = self.agent.plan(user_message)
            state.append(plan)
            envelopes.append(
                Envelope(EventType.AGENT_PLAN, session_id, "agent.runtime", asdict(plan), next_seq(), correlation_id=user_message.id)
            )

            tool_outputs: List[str] = []
            parsed = self._parse_tool_command(user_message.content)
            if parsed:
                tool_name, arg = parsed
                envelopes.append(
                    Envelope(
                        EventType.TOOL_CALL,
                        session_id,
                        "core.engine",
                        {"tool": tool_name, "arg": arg},
                        next_seq(),
                        correlation_id=user_message.id,
                    )
                )
                try:
                    result = self.tools.call(tool_name, arg)
                except KeyError:
                    result = f"tool_not_found:{tool_name}"

                tool_outputs.append(f"{tool_name}({arg}) => {result}")
                envelopes.append(
                    Envelope(
                        event_type=EventType.TOOL_RESULT,
                        session_id=session_id,
                        source="toolkit.registry",
                        payload={"tool": tool_name, "arg": arg, "result": result},
                        sequence_id=next_seq(),
                        correlation_id=user_message.id,
                    )
                )

            response = self.agent.respond(user_message, tool_outputs=tool_outputs)
            state.append(response)
            for part in chunk_text(response.content):
                envelopes.append(
                    Envelope(
                        event_type=EventType.RESPONSE_CHUNK,
                        session_id=session_id,
                        source="agent.runtime",
                        payload={"chunk": part, "response_id": response.id},
                        sequence_id=next_seq(),
                        correlation_id=user_message.id,
                    )
                )

            envelopes.append(
                Envelope(EventType.RESPONSE_COMPLETED, session_id, "agent.runtime", asdict(response), next_seq(), correlation_id=user_message.id)
            )
        except (ValidationError, Exception) as exc:  # noqa: BLE001
            envelopes.append(
                Envelope(
                    EventType.ERROR,
                    session_id,
                    "core.engine",
                    {"error": str(exc), "message_id": user_message.id},
                    next_seq(),
                    correlation_id=user_message.id,
                )
            )

        for envelope in envelopes:
            self._emit(envelope)

        return envelopes

    def subscribe(self, event_type: EventType, handler) -> None:
        self.bus.subscribe(event_type, handler)

    def stream(self, session_id: str, text: str) -> Iterable[Envelope]:
        yield from self.ingest_user_message(session_id=session_id, text=text)

    def stream_bytes(self, session_id: str, text: str) -> bytes:
        buffer = StreamBuffer()
        for envelope in self.stream(session_id=session_id, text=text):
            buffer.push(envelope)
        return buffer.dump()

    def replay(self, session_id: str, from_sequence: int = 1) -> List[Envelope]:
        with self._state_lock:
            return self.event_log.replay(session_id=session_id, from_sequence=from_sequence)


    def stats(self) -> dict:
        with self._state_lock:
            return {
                "sessions": len(self.sessions.list_sessions()),
                "tools": len(self.tools.list_tools()),
                "subscribers": self.bus.stats(),
            }


    def reset_state(self) -> dict:
        with self._state_lock:
            self.sessions = SessionStore()
            self.event_log = EventLog()
            self.rate_limiter = RateLimiter(
                max_requests=self.rate_limiter.max_requests,
                window_seconds=self.rate_limiter.window_seconds,
            )
            self.tools = ToolRegistry()
            self._register_default_tools()
            return {"reset": True}


    def session_overview(self) -> dict:
        with self._state_lock:
            session_ids = self.sessions.list_sessions()
            return {
                "sessions": session_ids,
                "count": len(session_ids),
            }


    def remove_session(self, session_id: str) -> dict:
        with self._state_lock:
            removed = self.sessions.delete(session_id)
            return {"removed": removed, "session_id": session_id}


    def session_detail(self, session_id: str) -> dict:
        with self._state_lock:
            return self.sessions.detail(session_id)


    def export_session_events(self, session_id: str) -> list[dict]:
        events = self.replay(session_id=session_id, from_sequence=1)
        return [
            {
                "event_type": e.event_type.value,
                "sequence_id": e.sequence_id,
                "payload": e.payload,
            }
            for e in events
        ]


    def runtime_config_snapshot(self) -> dict:
        with self._state_lock:
            return {
                "rate_limit_requests": self.rate_limiter.max_requests,
                "rate_limit_window_sec": self.rate_limiter.window_seconds,
                "tools": self.tools.list_tools(),
            }


    def session_event_count(self, session_id: str) -> dict:
        with self._state_lock:
            return {"session_id": session_id, "events": self.event_log.session_count(session_id)}
