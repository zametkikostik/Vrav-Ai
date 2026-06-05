from __future__ import annotations

from typing import Iterable


def chunk_text(text: str, size: int = 32) -> Iterable[str]:
    for idx in range(0, len(text), size):
        yield text[idx : idx + size]
