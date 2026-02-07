"""Components for the task dispatch example."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4

from agentecs import component


class TaskStatus(StrEnum):
    """Task lifecycle states.

    Tasks flow through these states:
    - UNASSIGNED: In TaskQueue, waiting for agent assignment
    - IN_PROGRESS: Agent is actively working on the task
    - WAITING_FOR_INPUT: Agent needs user response to continue
    - COMPLETED: Task finished, agent ready for cleanup
    """

    UNASSIGNED = "unassigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"


@component
@dataclass
class Task:
    """A unit of work to be completed by an agent.

    Attributes:
        id: Unique identifier for tracking
        description: What the agent should accomplish
        status: Current lifecycle state
        result: Final answer (set when COMPLETED)
        user_query: Question posed to user (when WAITING_FOR_INPUT)
        user_response: User's answer to query
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    status: TaskStatus = TaskStatus.UNASSIGNED
    result: str | None = None
    user_query: str | None = None
    user_response: str | None = None


@component
@dataclass
class TaskQueue:
    """Singleton component holding unassigned tasks."""

    tasks: list[Task] = field(default_factory=list)

    def add_task(self, description: str) -> Task:
        """Create and add a new unassigned task."""
        task = Task(description=description, status=TaskStatus.UNASSIGNED)
        self.tasks.append(task)
        return task


@component
@dataclass
class AgentState:
    """Agent's reasoning state and conversation history."""

    system_prompt: str = ""
    conversation_history: list[dict] = field(default_factory=list)
    iteration_count: int = 0
