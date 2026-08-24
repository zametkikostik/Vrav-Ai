from __future__ import annotations

import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from core.config import VravConfig
from core.engine import VravEngine
from core.modules.protocol.stream_protocol import StreamProtocol
from core.version import APP_NAME, APP_VERSION


class VravHttpHandler(BaseHTTPRequestHandler):
    config = VravConfig.from_env()
    engine = VravEngine()
    started_at = time.time()

    @classmethod
    def refresh_runtime_config(cls) -> None:
        cls.config = VravConfig.from_env()
        cls.engine.rate_limiter.max_requests = cls.config.rate_limit_requests
        cls.engine.rate_limiter.window_seconds = cls.config.rate_limit_window_sec

    def _request_id(self) -> str:
        rid = self.headers.get("X-Request-ID")
        return rid if rid else str(uuid4())

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return

        parsed = urlparse(self.path)

        self.refresh_runtime_config()

        if parsed.path == "/ping":
            self._json_response({"pong": True}, HTTPStatus.OK)
            return

        if parsed.path == "/time":
            self._json_response({"epoch": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, HTTPStatus.OK)
            return

        if parsed.path == "/whoami":
            self._json_response({
                "service": "vrav-core",
                "auth_enabled": self.config.auth_enabled(),
                "request_id": self._request_id(),
            }, HTTPStatus.OK)
            return

        if parsed.path == "/health":
            self._json_response({
                "status": "ok",
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "service": "vrav-core",
                "version": APP_VERSION,
            }, HTTPStatus.OK)
            return

        if parsed.path == "/status":
            stats = self.engine.stats()
            self._json_response({
                "status": "ok",
                "service": "vrav-core",
                "version": APP_VERSION,
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "sessions": stats["sessions"],
                "tools": stats["tools"],
                "production_ready": False,
            }, HTTPStatus.OK)
            return

        if parsed.path == "/version":
            self._json_response({"name": APP_NAME, "version": APP_VERSION}, HTTPStatus.OK)
            return

        if parsed.path == "/build":
            self._json_response({
                "name": APP_NAME,
                "version": APP_VERSION,
                "python": "3.12",
                "runtime": "threadinghttpserver",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/capabilities":
            self._json_response({
                "streaming": True,
                "replay": True,
                "snapshot_restore": True,
                "dynamic_tools": True,
                "sessions_api": True,
                "metrics": True,
                "openapi": True,
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/events":
            self._json_response({
                "event_fields": ["event_type", "session_id", "source", "payload", "sequence_id", "correlation_id", "idempotency_key", "id", "created_at"],
                "message_fields": ["role", "content", "metadata", "id", "created_at"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/events-query":
            self._json_response({
                "endpoint": "/events",
                "query_fields": ["session_id", "from_sequence", "limit"],
                "defaults": {"from_sequence": 1, "limit": 100},
                "response_fields": ["events", "count"],
                "event_projection_fields": ["event_type", "sequence_id", "payload"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/tools":
            self._json_response({
                "command": "/tool <name> <arg>",
                "tool_spec_fields": ["name", "description"],
                "tool_events": ["tool.call", "tool.result"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/tools-admin":
            self._json_response({
                "register_endpoint": "/tools/register",
                "unregister_endpoint": "/tools/unregister?name=<tool>",
                "register_payload_fields": ["name", "prefix"],
                "name_pattern": "^[A-Za-z][A-Za-z0-9_-]{0,63}$",
                "register_response_fields": ["registered"],
                "unregister_response_fields": ["removed", "name"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/tools-list":
            self._json_response({
                "endpoint": "/tools",
                "response_fields": ["tools"],
                "tool_fields": ["name", "description"],
                "default_tools": ["echo", "upper"],
                "dynamic_tools": True,
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/sessions":
            self._json_response({
                "overview_fields": ["sessions", "count"],
                "detail_fields": ["session_id", "messages", "last_sequence"],
                "count_fields": ["session_id", "events"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/session-ops":
            self._json_response({
                "overview_endpoint": "/sessions",
                "detail_endpoint": "/sessions?session_id=<id>",
                "export_endpoint": "/sessions/export?session_id=<id>",
                "count_endpoint": "/sessions/count?session_id=<id>",
                "delete_endpoint": "DELETE /sessions?session_id=<id>",
                "required_query_fields": ["session_id"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/system":
            self._json_response({
                "health_fields": ["status", "uptime_seconds", "service", "version"],
                "status_fields": ["status", "service", "version", "uptime_seconds", "sessions", "tools", "production_ready"],
                "build_fields": ["name", "version", "python", "runtime"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/runtime":
            self._json_response({
                "config_fields": ["auth_enabled", "rate_limit_requests", "rate_limit_window_sec", "engine"],
                "diagnostics_fields": ["service", "version", "uptime_seconds", "stats", "config", "auth_enabled"],
                "metrics_lines": ["vrav_sessions", "vrav_tools"],
                "slo_fields": ["service", "targets", "note"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/http":
            self._json_response({
                "headers": ["Content-Type", "Content-Length", "X-Request-ID"],
                "auth_header": "Authorization: Bearer <token>",
                "stream_content_type": "text/event-stream; charset=utf-8",
                "json_content_type": "application/json",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/auth":
            self._json_response({
                "auth_modes": ["disabled", "bearer_token"],
                "env_var": "VRAV_API_TOKEN",
                "required_header": "Authorization: Bearer <token>",
                "unauthorized_response": {"error": "unauthorized"},
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/errors":
            self._json_response({
                "envelope": {"error": "<code>"},
                "common_codes": [
                    "unauthorized",
                    "not_found",
                    "session_id_required",
                    "name_required",
                    "invalid_tool_name",
                    "invalid_json",
                    "invalid_query_param",
                    "invalid_snapshot",
                ],
                "examples": {
                    "unauthorized": {"status": 401, "body": {"error": "unauthorized"}},
                    "not_found": {"status": 404, "body": {"error": "not_found"}},
                    "invalid_tool_name": {"status": 400, "body": {"error": "invalid_tool_name"}},
                    "invalid_json": {"status": 400, "body": {"error": "invalid_json"}},
                    "invalid_query_param": {"status": 400, "body": {"error": "invalid_query_param", "field": "limit"}},
                    "invalid_snapshot": {"status": 400, "body": {"error": "invalid_snapshot"}},
                    "validation": {"status": 400, "body": {"error": "session_id_required"}},
                },
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/rate-limit":
            self._json_response({
                "runtime_config_fields": ["rate_limit_requests", "rate_limit_window_sec"],
                "stats_fields": ["rate_limit_requests", "rate_limit_window_sec"],
                "scope": "per session_id",
                "error_event_type": "error",
                "error_signal": "rate_limit_exceeded",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/snapshot":
            self._json_response({
                "snapshot_endpoint": "GET /snapshot?path=<file>",
                "restore_endpoint": "POST /restore",
                "restore_payload_fields": ["path"],
                "default_path": "/tmp/vrav_snapshot.json",
                "responses": {
                    "snapshot": ["ok", "path"],
                    "restore": ["restored", "path"],
                },
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/diagnostics":
            self._json_response({
                "endpoint": "/diagnostics",
                "fields": ["service", "version", "uptime_seconds", "stats", "config", "auth_enabled"],
                "related_endpoints": ["/stats", "/config", "/metrics", "/slo"],
                "auth_behavior": "inherits global auth guard",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/config":
            self._json_response({
                "endpoint": "/config",
                "fields": ["auth_enabled", "rate_limit_requests", "rate_limit_window_sec", "engine"],
                "engine_fields": ["max_history", "chunk_size", "max_session_events"],
                "auth_env_var": "VRAV_API_TOKEN",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/capabilities":
            self._json_response({
                "endpoint": "/capabilities",
                "fields": ["streaming", "replay", "snapshot_restore", "dynamic_tools", "sessions_api", "metrics", "openapi"],
                "value_type": "boolean",
                "purpose": "feature discovery for clients",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/readiness":
            self._json_response({
                "endpoint": "/readiness",
                "fields": [
                    "stage",
                    "production_ready",
                    "readiness_score_pct",
                    "remaining_to_initial_production_baseline",
                    "remaining_to_enterprise_hardening",
                    "blockers",
                    "next_doc",
                ],
                "stage_values": ["prototype"],
                "score_semantics": "0 means not started, 100 means production baseline satisfied",
                "readiness_doc": "docs/PRODUCTION_READINESS.md",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/slo":
            self._json_response({
                "endpoint": "/slo",
                "fields": ["service", "targets", "note"],
                "target_fields": ["availability", "p95_latency_ms", "error_rate_pct"],
                "purpose": "prototype targets for pre-production planning",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/liveness":
            self._json_response({
                "endpoints": ["/ping", "/time", "/whoami"],
                "ping_fields": ["pong"],
                "time_fields": ["epoch", "iso"],
                "whoami_fields": ["service", "auth_enabled", "request_id"],
                "request_id_header": "X-Request-ID",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/build":
            self._json_response({
                "endpoint": "/build",
                "fields": ["name", "version", "python", "runtime"],
                "runtime_values": ["threadinghttpserver"],
                "version_source": "core.version",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/routes":
            self._json_response({
                "endpoint": "/routes",
                "fields": ["routes"],
                "route_format": "<METHOD> <PATH>",
                "purpose": "human-readable route discovery",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/openapi":
            self._json_response({
                "endpoint": "/openapi.json",
                "fields": ["openapi", "info", "paths"],
                "openapi_version": "3.0.0",
                "path_item_methods": ["get", "post", "delete"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/stats":
            self._json_response({
                "endpoint": "/stats",
                "fields": ["sessions", "tools", "subscribers", "rate_limit_requests", "rate_limit_window_sec"],
                "source": "VravEngine.stats plus runtime rate-limit config",
                "related_endpoints": ["/metrics", "/diagnostics", "/schema/metrics"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/cli":
            self._json_response({
                "commands": [
                    "chat", "stream", "replay", "sessions", "session",
                    "session-export", "session-count", "reset", "config", "diagnostics"
                ],
                "entrypoint": "python -m core.cli",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/index":
            self._json_response({
                "schemas": [
                    "/schema/events",
                    "/schema/events-query",
                    "/schema/tools",
                    "/schema/tools-admin",
                    "/schema/tools-list",
                    "/schema/sessions",
                    "/schema/session-ops",
                    "/schema/system",
                    "/schema/runtime",
                    "/schema/http",
                    "/schema/auth",
                    "/schema/errors",
                    "/schema/rate-limit",
                    "/schema/snapshot",
                    "/schema/diagnostics",
                    "/schema/config",
                    "/schema/capabilities",
                    "/schema/readiness",
                    "/schema/slo",
                    "/schema/liveness",
                    "/schema/build",
                    "/schema/routes",
                    "/schema/openapi",
                    "/schema/stats",
                    "/schema/cli",
                    "/schema/replay",
                ]
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/discovery":
            self._json_response({
                "index": "/schema/index",
                "families": {
                    "event": ["/schema/events", "/schema/events-query"],
                    "tooling": ["/schema/tools", "/schema/tools-admin", "/schema/tools-list"],
                    "sessions": ["/schema/sessions", "/schema/session-ops"],
                    "system": ["/schema/system", "/schema/runtime", "/schema/http", "/schema/auth"],
                    "errors": ["/schema/errors"],
                    "traffic": ["/schema/rate-limit"],
                    "storage": ["/schema/snapshot"],
                    "admin": ["/schema/admin", "/schema/admin-reset"],
                    "observability": ["/schema/diagnostics", "/schema/runtime", "/schema/metrics", "/schema/config"],
                    "feature_discovery": ["/schema/capabilities"],
                    "readiness": ["/schema/readiness"],
                    "slo": ["/schema/slo"],
                    "liveness": ["/schema/liveness"],
                    "build": ["/schema/build"],
                    "route_discovery": ["/schema/routes"],
                    "api_description": ["/schema/openapi"],
                    "stats": ["/schema/stats"],
                    "streaming": ["/schema/stream", "/schema/stream-request"],
                    "replay": ["/schema/replay"],
                    "cli": ["/schema/cli"],
                },
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/version":
            self._json_response({
                "fields": ["name", "version"],
                "source": "core.version",
                "endpoints": ["/version", "/build", "/status", "/health"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/health":
            self._json_response({
                "endpoint": "/health",
                "fields": ["status", "uptime_seconds", "service", "version"],
                "status_values": ["ok"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/status":
            self._json_response({
                "endpoint": "/status",
                "fields": ["status", "service", "version", "uptime_seconds", "sessions", "tools", "production_ready"],
                "status_values": ["ok"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/stream":
            self._json_response({
                "sse_frame": ["event", "id", "data"],
                "stream_endpoint": "/stream",
                "replay_endpoints": ["/events", "/replay", "/sessions/export"],
                "content_type": "text/event-stream; charset=utf-8",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/stream-request":
            self._json_response({
                "endpoint": "POST /stream",
                "request_fields": ["session_id", "text"],
                "field_types": {"session_id": "string", "text": "string"},
                "validation_errors": ["empty_message", "message_too_large", "message_must_be_string"],
                "default_session_id": "default",
                "response_content_type": "text/event-stream; charset=utf-8",
                "response_headers": ["Cache-Control", "X-Request-ID"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/replay":
            self._json_response({
                "replay_endpoint": "/replay",
                "events_endpoint": "/events",
                "session_export_endpoint": "/sessions/export?session_id=<id>",
                "sequence_model": "monotonic per process",
                "format": "Envelope[]",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/admin":
            self._json_response({
                "reset_endpoint": "/admin/reset",
                "tool_register_endpoint": "/tools/register",
                "tool_unregister_endpoint": "/tools/unregister?name=<tool>",
                "session_delete_endpoint": "/sessions?session_id=<id>",
                "snapshot_endpoints": ["/snapshot", "/restore"],
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/admin-reset":
            self._json_response({
                "endpoint": "POST /admin/reset",
                "request_body": "{}",
                "response_fields": ["reset"],
                "side_effects": ["clears event log", "clears session store", "restores default tools", "resets rate limiter"],
                "auth_behavior": "inherits global auth guard",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/schema/metrics":
            self._json_response({
                "endpoint": "/metrics",
                "content_type": "text/plain; version=0.0.4",
                "lines": ["vrav_sessions", "vrav_tools"],
                "source": "/stats",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/tools":
            self._json_response({"tools": self.engine.tools.list_tools()}, HTTPStatus.OK)
            return

        if parsed.path == "/sessions":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            if session_id:
                self._json_response(self.engine.session_detail(session_id), HTTPStatus.OK)
                return
            self._json_response(self.engine.session_overview(), HTTPStatus.OK)
            return

        if parsed.path == "/sessions/export":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            if not session_id:
                self._json_response({"error": "session_id_required"}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response({"events": self.engine.export_session_events(session_id)}, HTTPStatus.OK)
            return

        if parsed.path == "/sessions/count":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            if not session_id:
                self._json_response({"error": "session_id_required"}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(self.engine.session_event_count(session_id), HTTPStatus.OK)
            return

        if parsed.path == "/config":
            self._json_response({
                "auth_enabled": self.config.auth_enabled(),
                "rate_limit_requests": self.config.rate_limit_requests,
                "rate_limit_window_sec": self.config.rate_limit_window_sec,
                "engine": self.engine.runtime_config_snapshot(),
            }, HTTPStatus.OK)
            return

        if parsed.path == "/diagnostics":
            stats = self.engine.stats()
            cfg = self.engine.runtime_config_snapshot()
            self._json_response({
                "service": "vrav-core",
                "version": APP_VERSION,
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "stats": stats,
                "config": cfg,
                "auth_enabled": self.config.auth_enabled(),
            }, HTTPStatus.OK)
            return

        if parsed.path == "/slo":
            self._json_response({
                "service": "vrav-core",
                "targets": {
                    "availability": "99.5%",
                    "p95_latency_ms": 800,
                    "error_rate_pct": 1.0,
                },
                "note": "prototype targets for pre-production planning",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/stats":
            stats = self.engine.stats()
            stats["rate_limit_requests"] = self.config.rate_limit_requests
            stats["rate_limit_window_sec"] = self.config.rate_limit_window_sec
            self._json_response(stats, HTTPStatus.OK)
            return

        if parsed.path == "/metrics":
            st = self.engine.stats()
            payload = (
                f"vrav_sessions {st['sessions']}\n"
                f"vrav_tools {st['tools']}\n"
            )
            self._text_response(payload, HTTPStatus.OK)
            return

        if parsed.path == "/readiness":
            self._json_response({
                "stage": "prototype",
                "production_ready": False,
                "readiness_score_pct": 25,
                "remaining_to_initial_production_baseline": "~6-10 weeks",
                "remaining_to_enterprise_hardening": "~12-16 weeks",
                "blockers": [
                    "durable_storage",
                    "distributed_rate_limiting",
                    "hardened_authz",
                    "observability_alerting",
                    "secure_tool_sandbox",
                    "deployment_runbooks",
                ],
                "next_doc": "docs/PRODUCTION_READINESS.md",
            }, HTTPStatus.OK)
            return

        if parsed.path == "/snapshot":
            query = parse_qs(parsed.query)
            path = query.get("path", ["/tmp/vrav_snapshot.json"])[0]
            try:
                self.engine.event_log.snapshot(path)
            except OSError:
                self._json_response({"error": "invalid_snapshot", "path": path}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response({"saved": True, "path": path}, HTTPStatus.OK)
            return

        if parsed.path == "/replay":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            from_seq = self._query_int(query, "from_sequence", default=1, minimum=1)
            if from_seq is None:
                return
            events = [event.payload for event in self.engine.replay(session_id, from_sequence=from_seq)]
            self._json_response({"events": events}, HTTPStatus.OK)
            return



        if parsed.path == "/openapi.json":
            spec = {
                "openapi": "3.0.0",
                "info": {"title": "VRAV Core API", "version": APP_VERSION},
                "paths": {
                    "/health": {"get": {}},
                    "/whoami": {"get": {}},
                    "/ping": {"get": {}},
                    "/time": {"get": {}},
                    "/version": {"get": {}},
                    "/build": {"get": {}},
                    "/capabilities": {"get": {}},
                    "/schema/events": {"get": {}},
                    "/schema/events-query": {"get": {}},
                    "/schema/tools": {"get": {}},
                    "/schema/tools-admin": {"get": {}},
                    "/schema/tools-list": {"get": {}},
                    "/schema/sessions": {"get": {}},
                    "/schema/session-ops": {"get": {}},
                    "/schema/system": {"get": {}},
                    "/schema/runtime": {"get": {}},
                    "/schema/http": {"get": {}},
                    "/schema/auth": {"get": {}},
                    "/schema/errors": {"get": {}},
                    "/schema/rate-limit": {"get": {}},
                    "/schema/snapshot": {"get": {}},
                    "/schema/diagnostics": {"get": {}},
                    "/schema/config": {"get": {}},
                    "/schema/capabilities": {"get": {}},
                    "/schema/readiness": {"get": {}},
                    "/schema/slo": {"get": {}},
                    "/schema/liveness": {"get": {}},
                    "/schema/build": {"get": {}},
                    "/schema/routes": {"get": {}},
                    "/schema/openapi": {"get": {}},
                    "/schema/stats": {"get": {}},
                    "/schema/cli": {"get": {}},
                    "/schema/index": {"get": {}},
                    "/schema/discovery": {"get": {}},
                    "/schema/version": {"get": {}},
                    "/schema/health": {"get": {}},
                    "/schema/status": {"get": {}},
                    "/schema/stream": {"get": {}},
                    "/schema/stream-request": {"get": {}},
                    "/schema/replay": {"get": {}},
                    "/schema/admin": {"get": {}},
                    "/schema/admin-reset": {"get": {}},
                    "/schema/metrics": {"get": {}},
                    "/status": {"get": {}},
                    "/tools": {"get": {}},
                    "/sessions": {"get": {}},
                    "/sessions/export": {"get": {}},
                    "/sessions/count": {"get": {}},
                    "/stats": {"get": {}},
                    "/config": {"get": {}},
                    "/diagnostics": {"get": {}},
                    "/slo": {"get": {}},
                    "/readiness": {"get": {}},
                    "/metrics": {"get": {}},
                    "/snapshot": {"get": {}},
                    "/replay": {"get": {}},
                    "/events": {"get": {}},
                    "/routes": {"get": {}},
                    "/stream": {"post": {}},
                    "/tools/register": {"post": {}},
                    "/restore": {"post": {}},
                    "/admin/reset": {"post": {}},
                    "/tools/unregister": {"delete": {}},
                    "/sessions": {"delete": {}},
                },
            }
            self._json_response(spec, HTTPStatus.OK)
            return

        if parsed.path == "/routes":
            self._json_response({
                "routes": [
                    "GET /health",
                    "GET /whoami",
                    "GET /ping",
                    "GET /time",
                    "GET /version",
                    "GET /build",
                    "GET /capabilities",
                    "GET /schema/events",
                    "GET /schema/events-query",
                    "GET /schema/tools",
                    "GET /schema/tools-admin",
                    "GET /schema/tools-list",
                    "GET /schema/sessions",
                    "GET /schema/session-ops",
                    "GET /schema/system",
                    "GET /schema/runtime",
                    "GET /schema/http",
                    "GET /schema/auth",
                    "GET /schema/errors",
                    "GET /schema/rate-limit",
                    "GET /schema/snapshot",
                    "GET /schema/diagnostics",
                    "GET /schema/config",
                    "GET /schema/capabilities",
                    "GET /schema/readiness",
                    "GET /schema/slo",
                    "GET /schema/liveness",
                    "GET /schema/build",
                    "GET /schema/routes",
                    "GET /schema/openapi",
                    "GET /schema/stats",
                    "GET /schema/cli",
                    "GET /schema/index",
                    "GET /schema/discovery",
                    "GET /schema/version",
                    "GET /schema/health",
                    "GET /schema/status",
                    "GET /schema/stream",
                    "GET /schema/stream-request",
                    "GET /schema/replay",
                    "GET /schema/admin",
                    "GET /schema/admin-reset",
                    "GET /schema/metrics",
                    "GET /status",
                    "GET /tools",
                    "GET /sessions",
                    "GET /sessions/export",
                    "GET /sessions/count",
                    "GET /sessions?session_id=<id>",
                    "GET /stats",
                    "GET /config",
                    "GET /diagnostics",
                    "GET /slo",
                    "GET /readiness",
                    "GET /metrics",
                    "GET /snapshot",
                    "GET /replay",
                    "GET /events",
                    "GET /routes",
                    "POST /stream",
                    "POST /tools/register",
                    "POST /restore",
                    "POST /admin/reset",
                    "DELETE /tools/unregister",
                    "DELETE /sessions",
                ]
            }, HTTPStatus.OK)
            return

        if parsed.path == "/events":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            from_seq = self._query_int(query, "from_sequence", default=1, minimum=1)
            limit = self._query_int(query, "limit", default=100, minimum=1)
            if from_seq is None or limit is None:
                return
            replayed = self.engine.replay(session_id, from_sequence=from_seq)
            events = [
                {
                    "event_type": e.event_type.value,
                    "sequence_id": e.sequence_id,
                    "payload": e.payload,
                }
                for e in replayed[:limit]
            ]
            self._json_response({"events": events, "count": len(events)}, HTTPStatus.OK)
            return

        self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)


    def _query_int(self, query: dict[str, list[str]], field: str, default: int, minimum: int = 1) -> int | None:
        raw = query.get(field, [str(default)])[0]
        try:
            value = int(raw)
        except (TypeError, ValueError):
            self._json_response({"error": "invalid_query_param", "field": field}, HTTPStatus.BAD_REQUEST)
            return None
        if value < minimum:
            self._json_response({"error": "invalid_query_param", "field": field}, HTTPStatus.BAD_REQUEST)
            return None
        return value

    def _authorized(self) -> bool:
        if not self.config.auth_enabled():
            return True
        token = self.headers.get("Authorization", "")
        return token == f"Bearer {self.config.api_token}"

    def _read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
            return None
        return data if isinstance(data, dict) else {}

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return

        self.refresh_runtime_config()

        if self.path == "/admin/reset":
            self._json_response(self.engine.reset_state(), HTTPStatus.OK)
            return

        if self.path == "/tools/register":
            data = self._read_json_body()
            if data is None:
                return
            name = str(data.get("name", "")).strip()
            prefix = str(data.get("prefix", ""))
            if not name:
                self._json_response({"error": "name_required"}, HTTPStatus.BAD_REQUEST)
                return

            try:
                self.engine.tools.register_lambda(
                    name=name,
                    description=f"Dynamic prefix tool for {name}",
                    fn=lambda arg, p=prefix: f"{p}{arg}",
                )
            except ValueError as exc:
                self._json_response({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response({"registered": name}, HTTPStatus.OK)
            return

        if self.path == "/restore":
            data = self._read_json_body()
            if data is None:
                return
            path = data.get("path", "/tmp/vrav_snapshot.json")
            try:
                count = self.engine.event_log.restore(path)
            except (OSError, ValueError, KeyError, TypeError):
                self._json_response({"error": "invalid_snapshot", "path": path}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response({"restored": count, "path": path}, HTTPStatus.OK)
            return

        if self.path != "/stream":
            self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        data = self._read_json_body()
        if data is None:
            return

        session_id = data.get("session_id", "default")
        text = data.get("text", "")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Request-ID", self._request_id())
        self.end_headers()

        for envelope in self.engine.stream(session_id=session_id, text=text):
            self.wfile.write(StreamProtocol.encode(envelope))

    def _text_response(self, payload: str, status: HTTPStatus) -> None:
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self._request_id())
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, payload: dict, status: HTTPStatus) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self._request_id())
        self.end_headers()
        self.wfile.write(body)

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json_response({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return

        parsed = urlparse(self.path)
        self.refresh_runtime_config()

        if parsed.path == "/tools/unregister":
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            if not name:
                self._json_response({"error": "name_required"}, HTTPStatus.BAD_REQUEST)
                return

            removed = self.engine.tools.unregister(name)
            self._json_response({"removed": removed, "name": name}, HTTPStatus.OK)
            return

        if parsed.path == "/sessions":
            query = parse_qs(parsed.query)
            session_id = query.get("session_id", [""])[0]
            if not session_id:
                self._json_response({"error": "session_id_required"}, HTTPStatus.BAD_REQUEST)
                return
            self._json_response(self.engine.remove_session(session_id), HTTPStatus.OK)
            return

        self._json_response({"error": "not_found"}, HTTPStatus.NOT_FOUND)


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), VravHttpHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_server()
