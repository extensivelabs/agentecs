"""Instructor adapter implementing LLMClient protocol.

Provides structured LLM output using the instructor library with support for
multiple providers: OpenAI, Anthropic, Google Gemini, and LiteLLM (100+ providers).

Usage:
    from pydantic import BaseModel
    from agentecs.adapters.instructor import InstructorAdapter
    from agentecs.adapters import Message

    class Analysis(BaseModel):
        sentiment: str
        confidence: float

    # From OpenAI client
    import openai
    adapter = InstructorAdapter.from_openai_client(openai.OpenAI())

    # From Anthropic client
    import anthropic
    adapter = InstructorAdapter.from_anthropic(anthropic.Anthropic())

    # From Google Gemini
    import google.generativeai as genai
    genai.configure(api_key="...")
    adapter = InstructorAdapter.from_gemini(genai.GenerativeModel("gemini-1.5-flash"))

    # From LiteLLM (100+ providers)
    from agentecs.config import LLMSettings
    adapter = InstructorAdapter.from_litellm(
        settings=LLMSettings(model="anthropic/claude-3-5-sonnet-20241022")
    )

    # Call with structured output
    messages = [Message.user("Analyze: Great product!")]
    result: Analysis = adapter.call(messages, response_model=Analysis)
    print(result.sentiment, result.confidence)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, TypeVar, cast

from agentecs.adapters.models import Message, MessageRole
from agentecs.config import LLMSettings

if TYPE_CHECKING:
    import instructor
    from openai import AsyncOpenAI, OpenAI

T = TypeVar("T")


def _messages_to_openai(messages: list[Message]) -> list[dict[str, str]]:
    """Convert Message objects to OpenAI message format."""
    role_map = {
        MessageRole.SYSTEM: "system",
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "assistant",
    }
    return [{"role": role_map[m.role], "content": m.content} for m in messages]


class InstructorAdapter:
    """Instructor-based implementation of LLMClient protocol.

    Uses instructor library for structured LLM output with Pydantic models.

    Attributes:
        client: The instructor-patched client.
        settings: LLM configuration settings.
    """

    def __init__(
        self,
        client: instructor.Instructor,
        settings: LLMSettings | None = None,
        async_client: instructor.AsyncInstructor | None = None,
    ) -> None:
        """Initialize adapter with instructor client.

        Use factory methods instead of direct construction.

        Args:
            client: Instructor-patched client for sync operations.
            settings: Optional LLM settings (uses defaults if None).
            async_client: Optional instructor-patched async client.
        """
        self._client = client
        self._async_client = async_client
        self._settings = settings or LLMSettings()

    @classmethod
    def from_instructor_client(
        cls,
        client: instructor.Instructor,
        settings: LLMSettings | None = None,
        async_client: instructor.AsyncInstructor | None = None,
    ) -> InstructorAdapter:
        """Create adapter from existing instructor client.

        Args:
            client: Instructor-patched client.
            settings: Optional LLM settings.
            async_client: Optional async instructor client.

        Returns:
            Configured InstructorAdapter instance.
        """
        return cls(client, settings, async_client)

    @classmethod
    def from_openai_client(
        cls,
        client: OpenAI,
        settings: LLMSettings | None = None,
        async_client: AsyncOpenAI | None = None,
        mode: instructor.Mode | None = None,
    ) -> InstructorAdapter:
        """Create adapter from OpenAI client.

        Wraps the OpenAI client with instructor for structured output.

        Args:
            client: OpenAI client instance.
            settings: Optional LLM settings.
            async_client: Optional async OpenAI client.
            mode: Instructor mode (default: TOOLS).

        Returns:
            Configured InstructorAdapter instance.
        """
        try:
            import instructor
        except ImportError as e:
            raise ImportError(
                "instructor is required for InstructorAdapter. "
                "Install with: pip install agentecs[llm]"
            ) from e

        mode = mode or instructor.Mode.TOOLS
        patched_client = instructor.from_openai(client, mode=mode)

        patched_async_client = None
        if async_client is not None:
            patched_async_client = instructor.from_openai(async_client, mode=mode)

        return cls(patched_client, settings, patched_async_client)

    @classmethod
    def from_anthropic(
        cls,
        client: Any,
        settings: LLMSettings | None = None,
        async_client: Any | None = None,
        mode: Any | None = None,
    ) -> InstructorAdapter:
        """Create adapter from Anthropic client.

        Wraps the Anthropic client with instructor for structured output.

        Args:
            client: anthropic.Anthropic client instance.
            settings: Optional LLM settings.
            async_client: Optional anthropic.AsyncAnthropic client.
            mode: instructor.Mode (default: ANTHROPIC_TOOLS).

        Returns:
            Configured InstructorAdapter instance.

        Example:
            ```python
            import anthropic
            from agentecs.adapters import InstructorAdapter

            client = anthropic.Anthropic()
            adapter = InstructorAdapter.from_anthropic(client)
            ```
        """
        try:
            import instructor
        except ImportError as e:
            raise ImportError(
                "instructor is required for InstructorAdapter. "
                "Install with: pip install agentecs[llm]"
            ) from e

        mode = mode or instructor.Mode.ANTHROPIC_TOOLS
        patched_client = instructor.from_anthropic(client, mode=mode)

        patched_async_client = None
        if async_client is not None:
            patched_async_client = instructor.from_anthropic(async_client, mode=mode)

        return cls(patched_client, settings, patched_async_client)  # type: ignore[arg-type]

    @classmethod
    def from_litellm(
        cls,
        settings: LLMSettings | None = None,
        mode: Any | None = None,
    ) -> InstructorAdapter:
        """Create adapter using LiteLLM for multi-provider support.

        LiteLLM provides a unified interface to 100+ LLM providers including
        OpenAI, Anthropic, Cohere, Azure, AWS Bedrock, and more.

        Args:
            settings: Optional LLM settings. The model field should use
                LiteLLM's provider/model format (e.g., "anthropic/claude-3-opus").
            mode: Instructor mode (default: TOOLS).

        Returns:
            Configured InstructorAdapter instance.

        Example:
            ```python
            from agentecs.adapters import InstructorAdapter
            from agentecs.config import LLMSettings

            # Use Claude via LiteLLM
            adapter = InstructorAdapter.from_litellm(
                settings=LLMSettings(model="anthropic/claude-3-5-sonnet-20241022")
            )

            # Use GPT-4 via LiteLLM
            adapter = InstructorAdapter.from_litellm(
                settings=LLMSettings(model="openai/gpt-4o")
            )
            ```
        """
        try:
            import instructor
            import litellm  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "instructor and litellm are required. "
                "Install with: pip install agentecs[llm] litellm"
            ) from e

        mode = mode or instructor.Mode.TOOLS
        patched_client = instructor.from_litellm(litellm.completion, mode=mode)
        patched_async_client = instructor.from_litellm(litellm.acompletion, mode=mode)

        return cls(patched_client, settings, patched_async_client)

    @classmethod
    def from_gemini(
        cls,
        client: Any,
        settings: LLMSettings | None = None,
        mode: Any | None = None,
    ) -> InstructorAdapter:
        """Create adapter from Google Gemini client.

        Wraps the Google GenerativeModel with instructor for structured output.

        Args:
            client: Google GenerativeModel instance.
            settings: Optional LLM settings.
            mode: Instructor mode (default: GEMINI_JSON).

        Returns:
            Configured InstructorAdapter instance.

        Example:
            ```python
            import google.generativeai as genai
            from agentecs.adapters import InstructorAdapter

            genai.configure(api_key="your-api-key")
            model = genai.GenerativeModel("gemini-1.5-flash")
            adapter = InstructorAdapter.from_gemini(model)
            ```
        """
        try:
            import instructor
        except ImportError as e:
            raise ImportError(
                "instructor is required for InstructorAdapter. "
                "Install with: pip install agentecs[llm] google-generativeai"
            ) from e

        mode = mode or instructor.Mode.GEMINI_JSON
        patched_client = instructor.from_gemini(client, mode=mode)

        # Gemini doesn't have a separate async client pattern
        return cls(patched_client, settings, None)

    @property
    def settings(self) -> LLMSettings:
        """Get the LLM settings."""
        return self._settings

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
            **kwargs: Additional parameters passed to the API.

        Returns:
            Validated response as the specified model type.
        """
        openai_messages = _messages_to_openai(messages)

        # Build kwargs with settings
        call_kwargs: dict[str, Any] = {
            "model": kwargs.pop("model", self._settings.model),
            "messages": openai_messages,
            "response_model": response_model,
            "temperature": temperature if temperature is not None else self._settings.temperature,
            "max_retries": kwargs.pop("max_retries", self._settings.max_retries),
        }

        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        elif self._settings.max_tokens is not None:
            call_kwargs["max_tokens"] = self._settings.max_tokens

        # Merge any additional kwargs
        call_kwargs.update(kwargs)

        return cast(T, self._client.chat.completions.create(**call_kwargs))

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
            **kwargs: Additional parameters passed to the API.

        Returns:
            Validated response as the specified model type.

        Raises:
            RuntimeError: If no async client was provided.
        """
        if self._async_client is None:
            raise RuntimeError(
                "No async client configured. Provide async_client when creating the adapter."
            )

        openai_messages = _messages_to_openai(messages)

        call_kwargs: dict[str, Any] = {
            "model": kwargs.pop("model", self._settings.model),
            "messages": openai_messages,
            "response_model": response_model,
            "temperature": temperature if temperature is not None else self._settings.temperature,
            "max_retries": kwargs.pop("max_retries", self._settings.max_retries),
        }

        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        elif self._settings.max_tokens is not None:
            call_kwargs["max_tokens"] = self._settings.max_tokens

        call_kwargs.update(kwargs)

        return cast(T, await self._async_client.chat.completions.create(**call_kwargs))

    def stream(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Stream LLM response with partial structured output.

        Uses instructor's Partial for incremental field population.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional parameters passed to the API.

        Yields:
            Partial response objects with incrementally populated fields.
        """
        try:
            from instructor import Partial
        except ImportError as e:
            raise ImportError(
                "instructor is required for streaming. Install with: pip install agentecs[llm]"
            ) from e

        openai_messages = _messages_to_openai(messages)

        call_kwargs: dict[str, Any] = {
            "model": kwargs.pop("model", self._settings.model),
            "messages": openai_messages,
            "response_model": Partial[response_model],  # type: ignore[valid-type]
            "temperature": temperature if temperature is not None else self._settings.temperature,
            "max_retries": kwargs.pop("max_retries", self._settings.max_retries),
            "stream": True,
        }

        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        elif self._settings.max_tokens is not None:
            call_kwargs["max_tokens"] = self._settings.max_tokens

        call_kwargs.update(kwargs)

        # Instructor returns an iterator of partial objects when streaming
        yield from self._client.chat.completions.create(**call_kwargs)

    async def stream_async(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Stream LLM response with partial structured output (async).

        Uses instructor's Partial for incremental field population.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional parameters passed to the API.

        Yields:
            Partial response objects with incrementally populated fields.

        Raises:
            RuntimeError: If no async client was provided.
        """
        if self._async_client is None:
            raise RuntimeError(
                "No async client configured. Provide async_client when creating the adapter."
            )

        try:
            from instructor import Partial
        except ImportError as e:
            raise ImportError(
                "instructor is required for streaming. Install with: pip install agentecs[llm]"
            ) from e

        openai_messages = _messages_to_openai(messages)

        call_kwargs: dict[str, Any] = {
            "model": kwargs.pop("model", self._settings.model),
            "messages": openai_messages,
            "response_model": Partial[response_model],  # type: ignore[valid-type]
            "temperature": temperature if temperature is not None else self._settings.temperature,
            "max_retries": kwargs.pop("max_retries", self._settings.max_retries),
            "stream": True,
        }

        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        elif self._settings.max_tokens is not None:
            call_kwargs["max_tokens"] = self._settings.max_tokens

        call_kwargs.update(kwargs)

        async for partial_obj in await self._async_client.chat.completions.create(**call_kwargs):
            yield partial_obj
