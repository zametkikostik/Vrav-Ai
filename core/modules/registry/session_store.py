from __future__ import annotations

from typing import Dict, List

from core.modules.schemas.models import SessionState


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def list_sessions(self) -> List[str]:
        return list(self._sessions)

    def history_size(self, session_id: str) -> int:
        return len(self.get_or_create(session_id).messages)


    def delete(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        return True


    def detail(self, session_id: str) -> dict:
        state = self.get_or_create(session_id)
        return {
            "session_id": session_id,
            "messages": len(state.messages),
            "last_sequence": state.last_sequence,
        }
