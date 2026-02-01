"""Task Dispatch App - AgentECS example with LLM agents.

Demonstrates:
- Dynamic agent spawning for tasks
- LLM-powered reasoning with structured outputs
- Multi-turn conversations with user interaction
- agentecs-viz integration for visualization
"""

from components import AgentState, Task, TaskQueue, TaskStatus
from models import AgentResponse, ResponseType
from systems import (
    agent_cleanup_system,
    agent_processing_system,
    task_assignment_system,
)
from world import EXAMPLE_TASKS, create_world, get_world_source

__all__ = [
    "AgentState",
    "AgentResponse",
    "EXAMPLE_TASKS",
    "ResponseType",
    "Task",
    "TaskQueue",
    "TaskStatus",
    "agent_cleanup_system",
    "agent_processing_system",
    "create_world",
    "get_world_source",
    "task_assignment_system",
]
