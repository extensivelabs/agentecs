"""LLM client setup for task dispatch example."""

from __future__ import annotations

import os

from anthropic import Anthropic, AsyncAnthropic

from agentecs.adapters.instructor import InstructorAdapter
from agentecs.config import LLMSettings

_llm_client: InstructorAdapter | None = None


def get_llm_client() -> InstructorAdapter:
    """Get or create the LLM client using AgentECS's InstructorAdapter."""
    global _llm_client

    if _llm_client is not None:
        return _llm_client

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise ValueError("No ANTHROPIC_API_KEY found. Set the environment variable to use Claude.")

    sync_client = Anthropic(api_key=anthropic_key)
    async_client = AsyncAnthropic(api_key=anthropic_key)

    settings = LLMSettings(
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
        if os.getenv("LLM_MAX_TOKENS")
        else 2000,
    )

    _llm_client = InstructorAdapter.from_anthropic(
        sync_client,
        settings=settings,
        async_client=async_client,
    )

    return _llm_client
