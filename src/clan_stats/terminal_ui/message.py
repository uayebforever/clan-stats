from typing import Any, Sequence, Mapping

from pydantic import BaseModel


class Message(BaseModel):
    message: str
    tokens: Sequence[Any]
    named_tokens: Mapping[str, Any]


def message_of(format_string: str, *tokens: Any, **named_tokens: Any) -> Message:
    return Message(
        message=format_string,
        tokens=tokens,
        named_tokens=named_tokens
    )


