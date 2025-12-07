"""Tests for InstructorAdapter.

Focus: Message conversion correctness, factory method wiring, settings propagation.
"""

from unittest.mock import MagicMock, patch

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


def test_from_openai_patches_sync_and_async_clients():
    """Factory patches both sync and async clients with correct mode.

    Why: Async client handling is easy to get wrong; mode selection matters.
    """
    mock_sync = MagicMock()
    mock_async = MagicMock()
    mock_patched_sync = MagicMock()
    mock_patched_async = MagicMock()
    mock_instructor = MagicMock()
    mock_instructor.Mode.TOOLS = "TOOLS"
    mock_instructor.from_openai.side_effect = [mock_patched_sync, mock_patched_async]

    with patch.dict("sys.modules", {"instructor": mock_instructor}):
        adapter = InstructorAdapter.from_openai_client(mock_sync, async_client=mock_async)

        assert mock_instructor.from_openai.call_count == 2
        assert adapter._client is mock_patched_sync
        assert adapter._async_client is mock_patched_async


def test_from_anthropic_uses_anthropic_tools_mode():
    """Anthropic factory uses correct mode default.

    Why: Wrong mode would break structured output.
    """
    mock_client = MagicMock()
    mock_instructor = MagicMock()
    mock_instructor.Mode.ANTHROPIC_TOOLS = "ANTHROPIC_TOOLS"
    mock_instructor.from_anthropic.return_value = MagicMock()

    with patch.dict("sys.modules", {"instructor": mock_instructor}):
        InstructorAdapter.from_anthropic(mock_client)

        mock_instructor.from_anthropic.assert_called_once_with(mock_client, mode="ANTHROPIC_TOOLS")


def test_from_litellm_creates_both_clients():
    """LiteLLM factory wires completion and acompletion functions.

    Why: LiteLLM is unique in taking functions rather than clients.
    """
    mock_instructor = MagicMock()
    mock_instructor.Mode.TOOLS = "TOOLS"
    mock_instructor.from_litellm.side_effect = [MagicMock(), MagicMock()]
    mock_litellm = MagicMock()

    with patch.dict("sys.modules", {"instructor": mock_instructor, "litellm": mock_litellm}):
        adapter = InstructorAdapter.from_litellm()

        # Should call from_litellm twice (sync + async)
        assert mock_instructor.from_litellm.call_count == 2
        assert adapter._async_client is not None


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
