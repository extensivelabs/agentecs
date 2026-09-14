"""LLM conversation models.

Defines types used by the LLMClient protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MessageRole(Enum):
    """Role of a message in LLM conversation."""

    SYSTEM = "developer"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Message:
    """A message in an LLM conversation.

    Attributes:
        role: Who sent the message.
        content: Message text content.
    """

    role: MessageRole
    content: str

    @classmethod
    def system(cls, content: str) -> Message:
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)
