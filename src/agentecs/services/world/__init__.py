"""World state and access management."""

from agentecs.services.world.access import EntityHandle, QueryResult, ScopedAccess
from agentecs.services.world.world import World

__all__ = [
    "EntityHandle",
    "QueryResult",
    "ScopedAccess",
    "World",
]
