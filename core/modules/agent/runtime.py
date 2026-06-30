from __future__ import annotations

from typing import List

from core.modules.schemas.models import EventType, Message, Role


class AgentRuntime:
    """Isolated orchestration runtime for agent decisions."""

    def plan(self, user_message: Message) -> Message:
        steps = self._build_plan(user_message.content)
        return Message(
            role=Role.AGENT,
            content="\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(steps)),
            metadata={
                "kind": EventType.AGENT_PLAN.value,
                "source_message_id": user_message.id,
                "steps": steps,
            },
        )

    def respond(self, user_message: Message, tool_outputs: List[str] | None = None) -> Message:
        tool_section = ""
        if tool_outputs:
            tool_section = "\nИнструменты:\n" + "\n".join(f"- {output}" for output in tool_outputs)

        answer = (
            "VRAV AI обработал запрос и подготовил ответ.\n"
            f"Запрос: {user_message.content}"
            f"{tool_section}\n"
            "Статус: готово к следующему шагу."
        )
        return Message(
            role=Role.AGENT,
            content=answer,
            metadata={"kind": EventType.RESPONSE_COMPLETED.value, "source_message_id": user_message.id},
        )

    def _build_plan(self, prompt: str) -> List[str]:
        return [
            "Определить цель пользователя и ограничения.",
            "Собрать контекст сессии и артефакты модулей.",
            f"Сформировать ответ по запросу: {prompt}",
        ]
