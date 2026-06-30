import json
import threading
import time
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from core.server import VravHttpHandler


def _run(server: ThreadingHTTPServer) -> None:
    server.serve_forever()


def test_handler_has_engine():
    assert VravHttpHandler.engine is not None


def test_health_endpoint_works():
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/health")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    payload = json.loads(body)
    assert payload["status"] == "ok"
    assert payload["service"] == "vrav-core"
    assert payload["version"] == "0.1.0"
    assert payload["uptime_seconds"] >= 0

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_post_stream_invalid_json_returns_bad_request():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("POST", "/stream", body="{bad", headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 400
    assert payload["error"] == "invalid_json"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_json_admin_post_endpoints_reject_invalid_json():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    for path in ("/tools/register", "/restore"):
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        conn.request("POST", path, body="{bad", headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        assert response.status == 400
        assert payload["error"] == "invalid_json"
        conn.close()

    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_stream_endpoint_returns_sse():
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "http-s1", "text": "hi"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})

    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    assert "event:" in body
    assert "data:" in body

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_tools_endpoint_works():
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/tools")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    tools = json.loads(body)["tools"]
    assert any(tool["name"] == "echo" for tool in tools)

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_snapshot_endpoint_works(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    snap = tmp_path / "snapshot.json"

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", f"/snapshot?path={snap}")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    assert json.loads(body)["saved"] is True
    assert snap.exists()

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_auth_guard_blocks_without_token_when_enabled(monkeypatch):
    monkeypatch.setenv("VRAV_API_TOKEN", "secret")
    from core.server import VravHttpHandler as HandlerWithAuth
    HandlerWithAuth.config = HandlerWithAuth.config.from_env()

    server = ThreadingHTTPServer(("127.0.0.1", 0), HandlerWithAuth)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/health")
    response = conn.getresponse()
    assert response.status == 401
    conn.close()

    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_auth_guard_allows_with_valid_token(monkeypatch):
    monkeypatch.setenv("VRAV_API_TOKEN", "secret")
    from core.server import VravHttpHandler as HandlerWithAuth
    HandlerWithAuth.config = HandlerWithAuth.config.from_env()

    server = ThreadingHTTPServer(("127.0.0.1", 0), HandlerWithAuth)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/health", headers={"Authorization": "Bearer secret"})
    response = conn.getresponse()
    assert response.status == 200
    conn.close()

    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_stats_endpoint_works():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/stats")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    data = json.loads(body)
    assert "sessions" in data
    assert "tools" in data

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_register_tool_endpoint_and_use_it():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"name": "prefixer", "prefix": "ok:"})
    conn.request("POST", "/tools/register", body=payload, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    assert response.status == 200
    response.read()

    stream_payload = json.dumps({"session_id": "dyn-tool", "text": "/tool prefixer world"})
    conn.request("POST", "/stream", body=stream_payload, headers={"Content-Type": "application/json"})
    stream_response = conn.getresponse()
    body = stream_response.read().decode("utf-8")

    assert stream_response.status == 200
    assert "ok:world" in body

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_events_endpoint_returns_envelopes():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "events-s1", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    _ = conn.getresponse()
    _.read()

    conn.request("GET", "/events?session_id=events-s1&from_sequence=1")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    events = json.loads(body)["events"]
    assert events
    assert "event_type" in events[0]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_unregister_tool_endpoint():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"name": "tmpx", "prefix": "x:"})
    conn.request("POST", "/tools/register", body=payload, headers={"Content-Type": "application/json"})
    reg = conn.getresponse()
    assert reg.status == 200
    reg.read()

    conn.request("DELETE", "/tools/unregister?name=tmpx")
    response = conn.getresponse()
    body = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert body["removed"] is True

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_readiness_endpoint_reports_prototype_stage():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/readiness")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["production_ready"] is False
    assert payload["stage"] == "prototype"
    assert payload["readiness_score_pct"] == 25
    assert payload["remaining_to_initial_production_baseline"] == "~6-10 weeks"
    assert "durable_storage" in payload["blockers"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_stats_includes_rate_limit_config(monkeypatch):
    monkeypatch.setenv("VRAV_RATE_LIMIT_REQUESTS", "77")
    monkeypatch.setenv("VRAV_RATE_LIMIT_WINDOW_SEC", "99")
    VravHttpHandler.config = VravHttpHandler.config.from_env()

    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/stats")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert data["rate_limit_requests"] == 77
    assert data["rate_limit_window_sec"] == 99

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_events_endpoint_honors_limit():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "events-limit", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("GET", "/events?session_id=events-limit&from_sequence=1&limit=1")
    response = conn.getresponse()
    body = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert body["count"] == 1
    assert len(body["events"]) == 1

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_version_endpoint_works():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/version")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["name"] == "vrav-ai"
    assert payload["version"] == "0.1.0"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_routes_endpoint_lists_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/routes")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "GET /health" in payload["routes"]
    assert "POST /stream" in payload["routes"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_openapi_endpoint_returns_spec():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/openapi.json")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["openapi"] == "3.0.0"
    assert "/stream" in payload["paths"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_request_id_echo_header():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/health", headers={"X-Request-ID": "req-123"})
    response = conn.getresponse()
    _ = response.read()

    assert response.status == 200
    assert response.getheader("X-Request-ID") == "req-123"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_admin_reset_clears_dynamic_tools():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"name": "rtool", "prefix": "r:"})
    conn.request("POST", "/tools/register", body=payload, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 200
    resp.read()

    conn.request("POST", "/admin/reset", body="{}", headers={"Content-Type": "application/json"})
    reset_resp = conn.getresponse()
    reset_payload = json.loads(reset_resp.read().decode("utf-8"))
    assert reset_resp.status == 200
    assert reset_payload["reset"] is True

    conn.request("GET", "/tools")
    tools_resp = conn.getresponse()
    tools_payload = json.loads(tools_resp.read().decode("utf-8"))
    names = [t["name"] for t in tools_payload["tools"]]
    assert "rtool" not in names

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_sessions_endpoint_lists_seen_sessions():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "sess-a", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("GET", "/sessions")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "sess-a" in data["sessions"]
    assert data["count"] >= 1

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_delete_session_endpoint_removes_session():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "delete-me", "text": "hi"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("DELETE", "/sessions?session_id=delete-me")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))
    assert response.status == 200
    assert data["removed"] is True

    conn.request("GET", "/sessions")
    sresp = conn.getresponse()
    spayload = json.loads(sresp.read().decode("utf-8"))
    assert "delete-me" not in spayload["sessions"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_sessions_detail_endpoint_returns_state():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "detail-1", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("GET", "/sessions?session_id=detail-1")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert data["session_id"] == "detail-1"
    assert data["messages"] >= 3
    assert data["last_sequence"] >= 1

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_metrics_endpoint_returns_plaintext_metrics():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/metrics")
    response = conn.getresponse()
    body = response.read().decode("utf-8")

    assert response.status == 200
    assert "vrav_sessions" in body
    assert "vrav_tools" in body

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_status_endpoint_aggregates_runtime_state():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/status")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["status"] == "ok"
    assert payload["service"] == "vrav-core"
    assert "sessions" in payload
    assert "tools" in payload

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_sessions_export_endpoint_returns_events():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "exp-1", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("GET", "/sessions/export?session_id=exp-1")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert data["events"]
    assert "event_type" in data["events"][0]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_restore_endpoint_rejects_invalid_snapshot_file(tmp_path):
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    bad_snapshot = tmp_path / "bad_snapshot.json"
    bad_snapshot.write_text("{bad", encoding="utf-8")

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"path": str(bad_snapshot)})
    conn.request("POST", "/restore", body=payload, headers={"Content-Type": "application/json"})
    response = conn.getresponse()
    body = json.loads(response.read().decode("utf-8"))

    assert response.status == 400
    assert body == {"error": "invalid_snapshot", "path": str(bad_snapshot)}

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_config_endpoint_returns_runtime_snapshot():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/config")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "auth_enabled" in payload
    assert "engine" in payload
    assert "tools" in payload["engine"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_sessions_count_endpoint_returns_event_total():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    payload = json.dumps({"session_id": "cnt-1", "text": "hello"})
    conn.request("POST", "/stream", body=payload, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    r.read()

    conn.request("GET", "/sessions/count?session_id=cnt-1")
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert data["session_id"] == "cnt-1"
    assert data["events"] >= 1

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_diagnostics_endpoint_aggregates_stats_and_config():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/diagnostics")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "stats" in payload
    assert "config" in payload
    assert payload["service"] == "vrav-core"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_slo_endpoint_returns_targets():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/slo")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["targets"]["p95_latency_ms"] == 800
    assert payload["targets"]["availability"] == "99.5%"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_whoami_endpoint_returns_auth_context():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/whoami", headers={"X-Request-ID": "who-1"})
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["service"] == "vrav-core"
    assert payload["auth_enabled"] is False
    assert payload["request_id"] == "who-1"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_ping_endpoint_returns_pong():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/ping")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["pong"] is True

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_time_endpoint_returns_epoch_and_iso():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/time")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert isinstance(payload["epoch"], float)
    assert payload["iso"].endswith("Z")

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_build_endpoint_returns_runtime_metadata():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/build")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["name"] == "vrav-ai"
    assert payload["version"] == "0.1.0"
    assert payload["runtime"] == "threadinghttpserver"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_capabilities_endpoint_returns_feature_flags():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/capabilities")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["streaming"] is True
    assert payload["dynamic_tools"] is True
    assert payload["openapi"] is True

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_events_endpoint_exposes_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/events")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "sequence_id" in payload["event_fields"]
    assert "content" in payload["message_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_events_endpoint_rejects_invalid_query_params():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/events?session_id=bad-query&limit=abc")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 400
    assert payload == {"error": "invalid_query_param", "field": "limit"}

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_replay_endpoint_rejects_invalid_from_sequence():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/replay?session_id=bad-query&from_sequence=0")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 400
    assert payload == {"error": "invalid_query_param", "field": "from_sequence"}

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_events_query_endpoint_exposes_events_query_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/events-query")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/events"
    assert "from_sequence" in payload["query_fields"]
    assert payload["defaults"]["limit"] == 100
    assert "count" in payload["response_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_tools_endpoint_exposes_tool_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/tools")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["command"].startswith("/tool")
    assert "tool.call" in payload["tool_events"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_tools_admin_endpoint_exposes_tool_admin_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/tools-admin")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["register_endpoint"] == "/tools/register"
    assert payload["unregister_endpoint"].startswith("/tools/unregister")
    assert "name" in payload["register_payload_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_tools_list_endpoint_exposes_tools_list_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/tools-list")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/tools"
    assert "tools" in payload["response_fields"]
    assert "name" in payload["tool_fields"]
    assert "echo" in payload["default_tools"]
    assert payload["dynamic_tools"] is True

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_sessions_endpoint_exposes_session_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/sessions")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "sessions" in payload["overview_fields"]
    assert "last_sequence" in payload["detail_fields"]
    assert "events" in payload["count_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_session_ops_endpoint_exposes_session_operations_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/session-ops")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["overview_endpoint"] == "/sessions"
    assert payload["export_endpoint"].startswith("/sessions/export")
    assert payload["delete_endpoint"].startswith("DELETE /sessions")
    assert "session_id" in payload["required_query_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_system_endpoint_exposes_system_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/system")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "uptime_seconds" in payload["health_fields"]
    assert "production_ready" in payload["status_fields"]
    assert "runtime" in payload["build_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_runtime_endpoint_exposes_runtime_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/runtime")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "auth_enabled" in payload["config_fields"]
    assert "stats" in payload["diagnostics_fields"]
    assert "vrav_sessions" in payload["metrics_lines"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_http_endpoint_exposes_transport_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/http")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "X-Request-ID" in payload["headers"]
    assert payload["json_content_type"] == "application/json"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_cli_endpoint_exposes_cli_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/cli")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "chat" in payload["commands"]
    assert payload["entrypoint"] == "python -m core.cli"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_index_endpoint_lists_schema_routes():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/index")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "/schema/events" in payload["schemas"]
    assert "/schema/cli" in payload["schemas"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_auth_endpoint_exposes_auth_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/auth")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["env_var"] == "VRAV_API_TOKEN"
    assert "bearer_token" in payload["auth_modes"]
    assert payload["unauthorized_response"]["error"] == "unauthorized"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_errors_endpoint_exposes_error_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/errors")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["envelope"] == {"error": "<code>"}
    assert "unauthorized" in payload["common_codes"]
    assert payload["examples"]["not_found"]["status"] == 404
    assert payload["examples"]["invalid_json"] == {
        "status": 400,
        "body": {"error": "invalid_json"},
    }
    assert payload["examples"]["invalid_query_param"] == {
        "status": 400,
        "body": {"error": "invalid_query_param", "field": "limit"},
    }
    assert payload["examples"]["invalid_snapshot"] == {
        "status": 400,
        "body": {"error": "invalid_snapshot"},
    }

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_rate_limit_endpoint_exposes_rate_limit_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/rate-limit")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["scope"] == "per session_id"
    assert "rate_limit_requests" in payload["runtime_config_fields"]
    assert payload["error_signal"] == "rate_limit_exceeded"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_snapshot_endpoint_exposes_snapshot_restore_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/snapshot")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["snapshot_endpoint"].startswith("GET /snapshot")
    assert payload["restore_endpoint"] == "POST /restore"
    assert "path" in payload["restore_payload_fields"]
    assert payload["default_path"] == "/tmp/vrav_snapshot.json"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_diagnostics_endpoint_exposes_diagnostics_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/diagnostics")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/diagnostics"
    assert "stats" in payload["fields"]
    assert "/metrics" in payload["related_endpoints"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_config_endpoint_exposes_runtime_config_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/config")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/config"
    assert "engine" in payload["fields"]
    assert "max_history" in payload["engine_fields"]
    assert payload["auth_env_var"] == "VRAV_API_TOKEN"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_capabilities_endpoint_exposes_feature_flags_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/capabilities")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/capabilities"
    assert "streaming" in payload["fields"]
    assert payload["value_type"] == "boolean"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_readiness_endpoint_exposes_readiness_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/readiness")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/readiness"
    assert "production_ready" in payload["fields"]
    assert "readiness_score_pct" in payload["fields"]
    assert "blockers" in payload["fields"]
    assert "prototype" in payload["stage_values"]
    assert payload["score_semantics"].startswith("0 means")
    assert payload["readiness_doc"] == "docs/PRODUCTION_READINESS.md"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_slo_endpoint_exposes_slo_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/slo")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/slo"
    assert "targets" in payload["fields"]
    assert "p95_latency_ms" in payload["target_fields"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_liveness_endpoint_exposes_liveness_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/liveness")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "/ping" in payload["endpoints"]
    assert "iso" in payload["time_fields"]
    assert "request_id" in payload["whoami_fields"]
    assert payload["request_id_header"] == "X-Request-ID"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_build_endpoint_exposes_build_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/build")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/build"
    assert "runtime" in payload["fields"]
    assert "threadinghttpserver" in payload["runtime_values"]
    assert payload["version_source"] == "core.version"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_routes_endpoint_exposes_routes_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/routes")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/routes"
    assert payload["fields"] == ["routes"]
    assert payload["route_format"] == "<METHOD> <PATH>"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_openapi_endpoint_exposes_openapi_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/openapi")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/openapi.json"
    assert "paths" in payload["fields"]
    assert payload["openapi_version"] == "3.0.0"
    assert "post" in payload["path_item_methods"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_stats_endpoint_exposes_stats_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/stats")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/stats"
    assert "sessions" in payload["fields"]
    assert "rate_limit_requests" in payload["fields"]
    assert "/metrics" in payload["related_endpoints"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_discovery_endpoint_groups_schema_families():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/discovery")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["index"] == "/schema/index"
    assert "/schema/events" in payload["families"]["event"]
    assert "/schema/cli" in payload["families"]["cli"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_version_endpoint_exposes_version_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/version")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert "name" in payload["fields"]
    assert "/version" in payload["endpoints"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_stream_endpoint_exposes_stream_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/stream")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["stream_endpoint"] == "/stream"
    assert "event" in payload["sse_frame"]
    assert payload["content_type"].startswith("text/event-stream")

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_stream_request_endpoint_exposes_stream_request_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/stream-request")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "POST /stream"
    assert "session_id" in payload["request_fields"]
    assert payload["default_session_id"] == "default"
    assert "X-Request-ID" in payload["response_headers"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_admin_endpoint_exposes_admin_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/admin")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["reset_endpoint"] == "/admin/reset"
    assert "/snapshot" in payload["snapshot_endpoints"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_admin_reset_endpoint_exposes_admin_reset_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/admin-reset")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "POST /admin/reset"
    assert "reset" in payload["response_fields"]
    assert "restores default tools" in payload["side_effects"]
    assert payload["auth_behavior"] == "inherits global auth guard"

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_metrics_endpoint_exposes_metrics_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/metrics")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/metrics"
    assert "vrav_sessions" in payload["lines"]
    assert payload["content_type"].startswith("text/plain")

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_health_endpoint_exposes_health_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/health")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/health"
    assert "uptime_seconds" in payload["fields"]
    assert "ok" in payload["status_values"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_status_endpoint_exposes_status_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/status")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["endpoint"] == "/status"
    assert "production_ready" in payload["fields"]
    assert "ok" in payload["status_values"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)


def test_schema_replay_endpoint_exposes_replay_contract():
    VravHttpHandler.config.api_token = ""
    server = ThreadingHTTPServer(("127.0.0.1", 0), VravHttpHandler)
    thread = threading.Thread(target=_run, args=(server,), daemon=True)
    thread.start()
    time.sleep(0.02)

    conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    conn.request("GET", "/schema/replay")
    response = conn.getresponse()
    payload = json.loads(response.read().decode("utf-8"))

    assert response.status == 200
    assert payload["replay_endpoint"] == "/replay"
    assert payload["events_endpoint"] == "/events"
    assert payload["format"] == "Envelope[]"
    assert "monotonic" in payload["sequence_model"]

    conn.close()
    server.shutdown()
    server.server_close()
    thread.join(timeout=1)
