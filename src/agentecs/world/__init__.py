"""World state and access management.

Architecture Note:
    world/ is a stateful service layer that coordinates entities, components,
    and systems. Unlike core/ (stateless functionalities), world/ maintains
    runtime state and orchestrates the ECS execution model.
"""

from agentecs.storage.allocator import EntityAllocator
from agentecs.world.access import (
    AccessViolationError,
    EntityHandle,
    QueryResult,
    ReadOnlyAccess,
    ScopedAccess,
)
from agentecs.world.result import ConflictError, SystemResult, SystemReturn, normalize_result
from agentecs.world.world import World

__all__ = [
    "ScopedAccess",
    "ReadOnlyAccess",
    "EntityHandle",
    "AccessViolationError",
    "QueryResult",
    "SystemResult",
    "SystemReturn",
    "normalize_result",
    "ConflictError",
    "World",
    "EntityAllocator",
]
