"""LLM client protocol for structured-output model calls."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol, TypeVar, runtime_checkable

from agentecs.models.llm import Message

T = TypeVar("T")


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM operations with structured output.

    Uses Pydantic models for type-safe responses.

    Usage:
        class Analysis(BaseModel):
            sentiment: str
            confidence: float

        client: LLMClient = InstructorAdapter.from_openai_client(openai_client)
        result: Analysis = client.call(messages, response_model=Analysis)
    """

    def call(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Call LLM with structured output.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Validated response as the specified model type.
        """
        ...

    async def call_async(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Call LLM with structured output (async).

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Validated response as the specified model type.
        """
        ...

    def stream(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Stream LLM response with partial structured output.

        Yields partial objects as they are received, with fields
        populated incrementally.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Partial response objects with incrementally populated fields.
        """
        ...

    def stream_async(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Stream LLM response with partial structured output (async).

        Yields partial objects as they are received, with fields
        populated incrementally.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Partial response objects with incrementally populated fields.
        """
        ...
