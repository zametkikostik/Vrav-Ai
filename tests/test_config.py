from core.config import VravConfig


def test_config_from_env_uses_rate_limit_overrides(monkeypatch):
    monkeypatch.setenv("VRAV_RATE_LIMIT_REQUESTS", "7")
    monkeypatch.setenv("VRAV_RATE_LIMIT_WINDOW_SEC", "9")

    cfg = VravConfig.from_env()

    assert cfg.rate_limit_requests == 7
    assert cfg.rate_limit_window_sec == 9


def test_config_from_env_falls_back_for_invalid_rate_limits(monkeypatch):
    monkeypatch.setenv("VRAV_RATE_LIMIT_REQUESTS", "not-int")
    monkeypatch.setenv("VRAV_RATE_LIMIT_WINDOW_SEC", "0")

    cfg = VravConfig.from_env()

    assert cfg.rate_limit_requests == 50
    assert cfg.rate_limit_window_sec == 60
