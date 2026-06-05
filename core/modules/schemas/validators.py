from __future__ import annotations

from core.modules.schemas.models import Message


class ValidationError(ValueError):
    pass


def validate_user_message(message: Message) -> None:
    content = message.content.strip()
    if not content:
        raise ValidationError("empty_message")
    if len(content) > 4000:
        raise ValidationError("message_too_large")
