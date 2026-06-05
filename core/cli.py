from __future__ import annotations

import argparse
import json

from core.engine import VravEngine
from core.modules.protocol.stream_protocol import StreamProtocol


def run_chat(session_id: str, text: str) -> None:
    engine = VravEngine()
    events = list(engine.stream(session_id=session_id, text=text))
    for event in events:
        print(json.dumps(event.payload, ensure_ascii=False, default=str))


def run_stream(session_id: str, text: str) -> None:
    engine = VravEngine()
    raw = engine.stream_bytes(session_id=session_id, text=text)
    decoded = list(StreamProtocol.decode(raw.decode("utf-8")))
    print(f"decoded_events={len(decoded)}")


def run_replay(session_id: str, from_sequence: int, limit: int) -> None:
    engine = VravEngine()
    events = engine.replay(session_id=session_id, from_sequence=from_sequence)[:limit]
    print(f"events={len(events)}")


def run_sessions() -> None:
    engine = VravEngine()
    overview = engine.session_overview()
    print(json.dumps(overview, ensure_ascii=False))


def run_session_detail(session_id: str) -> None:
    engine = VravEngine()
    detail = engine.session_detail(session_id)
    print(json.dumps(detail, ensure_ascii=False))


def run_session_export(session_id: str) -> None:
    engine = VravEngine()
    events = engine.export_session_events(session_id)
    print(json.dumps({"events": events}, ensure_ascii=False, default=str))


def run_session_count(session_id: str) -> None:
    engine = VravEngine()
    print(json.dumps(engine.session_event_count(session_id), ensure_ascii=False))


def run_reset() -> None:
    engine = VravEngine()
    print(json.dumps(engine.reset_state(), ensure_ascii=False))


def run_config() -> None:
    engine = VravEngine()
    print(json.dumps(engine.runtime_config_snapshot(), ensure_ascii=False, default=str))


def run_diagnostics() -> None:
    engine = VravEngine()
    print(json.dumps({
        "stats": engine.stats(),
        "config": engine.runtime_config_snapshot(),
    }, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(prog="vrav")
    sub = parser.add_subparsers(dest="cmd", required=True)

    chat = sub.add_parser("chat")
    chat.add_argument("--session", default="cli-session")
    chat.add_argument("--text", required=True)

    stream = sub.add_parser("stream")
    stream.add_argument("--session", default="cli-session")
    stream.add_argument("--text", required=True)

    replay = sub.add_parser("replay")
    replay.add_argument("--session", default="cli-session")
    replay.add_argument("--from-sequence", type=int, default=1)
    replay.add_argument("--limit", type=int, default=100)

    sub.add_parser("sessions")
    sdetail = sub.add_parser("session")
    sdetail.add_argument("--id", required=True)

    sexport = sub.add_parser("session-export")
    sexport.add_argument("--id", required=True)

    scount = sub.add_parser("session-count")
    scount.add_argument("--id", required=True)
    sub.add_parser("reset")
    sub.add_parser("config")
    sub.add_parser("diagnostics")

    args = parser.parse_args()

    if args.cmd == "chat":
        run_chat(args.session, args.text)
    elif args.cmd == "stream":
        run_stream(args.session, args.text)
    elif args.cmd == "replay":
        run_replay(args.session, args.from_sequence, args.limit)
    elif args.cmd == "sessions":
        run_sessions()
    elif args.cmd == "session":
        run_session_detail(args.id)
    elif args.cmd == "session-export":
        run_session_export(args.id)
    elif args.cmd == "session-count":
        run_session_count(args.id)
    elif args.cmd == "reset":
        run_reset()
    elif args.cmd == "config":
        run_config()
    elif args.cmd == "diagnostics":
        run_diagnostics()


if __name__ == "__main__":
    main()
