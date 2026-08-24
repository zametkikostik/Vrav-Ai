from core.engine import VravEngine
from core.modules.protocol.stream_protocol import StreamBuffer, StreamProtocol
from core.modules.schemas.models import EventType


def test_stream_produces_completion_event():
    engine = VravEngine()
    events = list(engine.stream("s1", "Привет"))
    assert events[0].event_type == EventType.USER_MESSAGE
    assert events[-1].event_type == EventType.RESPONSE_COMPLETED
    assert any(evt.event_type == EventType.RESPONSE_CHUNK for evt in events)


def test_stream_sequence_is_monotonic():
    engine = VravEngine()
    events = list(engine.stream("s2", "Сделай план"))
    sequence = [event.sequence_id for event in events]
    assert sequence == sorted(sequence)


def test_stream_bytes_can_be_decoded():
    engine = VravEngine()
    raw = engine.stream_bytes("s3", "Покажи протокол")
    decoded = list(StreamProtocol.decode(raw.decode("utf-8")))
    assert decoded[-1].event_type == EventType.RESPONSE_COMPLETED


def test_tool_result_event_is_emitted():
    engine = VravEngine()
    events = list(engine.stream("s4", "/tool echo vrav"))
    tool_events = [evt for evt in events if evt.event_type == EventType.TOOL_RESULT]
    assert tool_events
    assert tool_events[0].payload["result"] == "vrav"


def test_tool_call_event_is_emitted():
    engine = VravEngine()
    events = list(engine.stream("s-tool", "/tool upper vrav ai"))
    call_events = [evt for evt in events if evt.event_type == EventType.TOOL_CALL]
    assert call_events
    assert call_events[0].payload["tool"] == "upper"


def test_session_store_history_size():
    engine = VravEngine()
    list(engine.stream("s5", "one"))
    assert engine.sessions.history_size("s5") == 3


def test_replay_returns_session_events():
    engine = VravEngine()
    list(engine.stream("s6", "history"))
    replay = engine.replay("s6", from_sequence=2)
    assert replay
    assert replay[0].sequence_id >= 2


def test_empty_message_generates_error_event():
    engine = VravEngine()
    events = list(engine.stream("s7", "   "))
    assert events[-1].event_type == EventType.ERROR


def test_stream_buffer_clear_works():
    engine = VravEngine()
    events = list(engine.stream("s8", "hello"))
    buf = StreamBuffer()
    for event in events:
        buf.push(event)
    assert buf.dump()
    buf.clear()
    assert buf.dump() == b""


def test_eventlog_snapshot_restore(tmp_path):
    engine = VravEngine()
    list(engine.stream("persist-1", "hello"))
    path = tmp_path / "ev.json"
    engine.event_log.snapshot(str(path))

    restored = VravEngine()
    count = restored.event_log.restore(str(path))

    assert count > 0
    assert restored.replay("persist-1")


def test_rate_limiter_produces_error_after_limit():
    engine = VravEngine()
    engine.rate_limiter.max_requests = 1
    list(engine.stream("rl-1", "one"))
    events = list(engine.stream("rl-1", "two"))
    assert events[0].event_type == EventType.ERROR
    assert events[0].payload["error"] == "rate_limited"


def test_rate_limiter_error_is_persisted_for_replay():
    engine = VravEngine()
    engine.rate_limiter.max_requests = 1
    list(engine.stream("rl-persist", "one"))
    limited = list(engine.stream("rl-persist", "two"))

    replay = engine.replay("rl-persist")

    assert replay[-1].event_type == EventType.ERROR
    assert replay[-1].payload["error"] == "rate_limited"
    assert replay[-1].sequence_id == limited[0].sequence_id


def test_eventlog_restore_invalid_snapshot_is_atomic(tmp_path):
    engine = VravEngine()
    list(engine.stream("atomic-restore", "hello"))
    before = engine.event_log.session_count("atomic-restore")
    bad_snapshot = tmp_path / "bad.json"
    bad_snapshot.write_text("{bad", encoding="utf-8")

    try:
        engine.event_log.restore(str(bad_snapshot))
    except ValueError:
        pass

    assert engine.event_log.session_count("atomic-restore") == before


def test_non_string_message_generates_validation_error_event():
    engine = VravEngine()
    events = list(engine.stream("s-non-string", 123))  # type: ignore[arg-type]

    assert events[-1].event_type == EventType.ERROR
    assert events[-1].payload["error"] == "message_must_be_string"

