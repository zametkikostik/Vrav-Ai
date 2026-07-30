import subprocess


def test_cli_chat_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "chat", "--text", "hello"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip()


def test_cli_stream_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "stream", "--text", "hello"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "decoded_events" in result.stdout


def test_cli_replay_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "replay", "--session", "none", "--limit", "1"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "events=" in result.stdout


def test_cli_sessions_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "sessions"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "sessions" in result.stdout


def test_cli_reset_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "reset"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "reset" in result.stdout


def test_cli_session_detail_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "session", "--id", "demo"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "session_id" in result.stdout


def test_cli_session_export_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "session-export", "--id", "demo"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "events" in result.stdout


def test_cli_config_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "config"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "rate_limit_requests" in result.stdout


def test_cli_session_count_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "session-count", "--id", "demo"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "events" in result.stdout


def test_cli_diagnostics_command_runs():
    result = subprocess.run(
        ["python", "-m", "core.cli", "diagnostics"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "stats" in result.stdout
    assert "config" in result.stdout
