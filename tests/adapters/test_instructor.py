"""Tests for InstructorAdapter.

Focus: Message conversion correctness, factory method wiring, settings propagation.
"""

from unittest.mock import MagicMock

import pytest

from agentecs.adapters.instructor import InstructorAdapter, _messages_to_openai
from agentecs.adapters.models import Message
from agentecs.config import LLMSettings


def test_messages_to_openai_preserves_order_and_roles():
    """Message conversion preserves order and maps roles correctly.

    Why: Incorrect role mapping or order would break LLM conversations.
    """
    messages = [
        Message.system("Be helpful"),
        Message.user("Hi"),
        Message.assistant("Hello!"),
        Message.user("Thanks"),
    ]
    result = _messages_to_openai(messages)

    assert result == [
        {"role": "system", "content": "Be helpful"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Thanks"},
    ]


def test_call_propagates_settings_to_api():
    """Settings are passed through to the underlying API call.

    Why: Settings not propagating would silently use wrong model/temp.
    """
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = {"result": "test"}

    settings = LLMSettings(model="test-model", temperature=0.3, max_retries=5, max_tokens=500)
    adapter = InstructorAdapter.from_instructor_client(mock_client, settings=settings)

    class ResponseModel:
        pass

    adapter.call([Message.user("test")], ResponseModel)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "test-model"
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["max_retries"] == 5
    assert call_kwargs["max_tokens"] == 500


def test_call_async_requires_async_client():
    """Async call without async client raises clear error.

    Why: Silent failure or cryptic error would confuse users.
    """
    mock_client = MagicMock()
    adapter = InstructorAdapter.from_instructor_client(mock_client, async_client=None)

    class ResponseModel:
        pass

    with pytest.raises(RuntimeError, match="No async client configured"):
        import asyncio

        asyncio.run(adapter.call_async([Message.user("test")], ResponseModel))
