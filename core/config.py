from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class VravConfig:
    api_token: str = ""
    rate_limit_requests: int = 50
    rate_limit_window_sec: int = 60

    @classmethod
    def from_env(cls) -> "VravConfig":
        return cls(
            api_token=os.getenv("VRAV_API_TOKEN", ""),
            rate_limit_requests=int(os.getenv("VRAV_RATE_LIMIT_REQUESTS", "50")),
            rate_limit_window_sec=int(os.getenv("VRAV_RATE_LIMIT_WINDOW_SEC", "60")),
        )

    def auth_enabled(self) -> bool:
        return bool(self.api_token)
