"""World setup and agentecs-viz integration."""

from __future__ import annotations

from components import TaskQueue
from systems import (
    agent_cleanup_system,
    agent_processing_system,
    task_assignment_system,
)

from agentecs import World

EXAMPLE_TASKS = [
    "Plan a weekend trip to a nearby city",
    "Recommend a book for someone who likes sci-fi",
    "Write a haiku about programming",
]


def create_world(tasks: list[str] | None = None) -> World:
    """Create a World with task dispatch systems."""
    world = World()

    queue = TaskQueue()
    for desc in tasks or EXAMPLE_TASKS:
        queue.add_task(desc)
    world.set_singleton(queue)

    world.register_system(task_assignment_system)
    world.register_system(agent_processing_system)
    world.register_system(agent_cleanup_system)

    return world


def get_world_source():
    """Get WorldStateSource for agentecs-viz integration."""
    from agentecs_viz.history import HistoryCapturingSource
    from agentecs_viz.sources.local import LocalWorldSource

    return HistoryCapturingSource(LocalWorldSource(create_world()))
