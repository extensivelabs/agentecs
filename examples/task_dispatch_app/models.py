"""Pydantic Response Models for Agent LLM Interaction."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResponseType(str, Enum):
    """Agent response action types.

    - DEEP_THOUGHT: Agent needs more thinking time, message contains reasoning
    - ASK_USER: Agent needs clarification, message contains question for user
    - FINAL_ANSWER: Task complete, message contains final result
    """

    DEEP_THOUGHT = "deep_thought"
    ASK_USER = "ask_user"
    FINAL_ANSWER = "final_answer"


class AgentResponse(BaseModel):
    """Provide the response of the agent."""

    reasoning: str = Field(
        ...,
        description=(
            "In four sentences or less, summarize what you know, then assess "
            "each of the three response types. Choose the most appropriate one."
        ),
    )
    response_type: ResponseType = Field(
        ...,
        description=(
            "The action you want to take: "
            "DEEP_THOUGHT if you need more time to think, "
            "ASK_USER if you need clarification from the user, "
            "FINAL_ANSWER if you've completed the task."
        ),
    )
    message: str = Field(
        ...,
        description=(
            "Based on response_type: "
            "For DEEP_THOUGHT, describe what you're considering (brief). "
            "For ASK_USER, write your question in 1-2 sentences maximum - be concise and specific. "
            "For FINAL_ANSWER, provide your complete result."
        ),
    )
