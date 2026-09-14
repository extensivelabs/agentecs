"""AgentECS: Entity Component System for AI Agent Orchestration.

Usage:
    from agentecs import World, component, system, EntityId

    @component
    @dataclass
    class Position:
        x: float
        y: float

    @system(reads=(Position,), writes=(Position,))
    def move_right(world):
        for entity, pos in world(Position):
            world[entity, Position] = Position(pos.x + 1, pos.y)

    world = World()
    entity = world.spawn(Position(0, 0))
    world.register_system(move_right)
    world.tick()
"""

__version__ = "0.1.0"

from agentecs.api import World, component, system
from agentecs.models import (
    AccessViolationError,
    Combinable,
    Copy,
    EntityId,
    MutationOp,
    OpKind,
    Query,
    SchedulerConfig,
    Splittable,
    SystemEntity,
    SystemMode,
    SystemResult,
    TickRecord,
)
from agentecs.protocols import HistoryStore, ReadOnlyAccess, Storage
from agentecs.services.scheduler import SequentialScheduler, SimpleScheduler
from agentecs.services.storage import LocalStorage
from agentecs.services.world import ScopedAccess

__all__ = [
    # Version
    "__version__",
    # Core
    "Copy",
    "EntityId",
    "SystemEntity",
    "component",
    "system",
    "SystemMode",
    "Query",
    "Combinable",
    "Splittable",
    # World
    "World",
    "ScopedAccess",
    "ReadOnlyAccess",
    "SystemResult",
    "MutationOp",
    "OpKind",
    "AccessViolationError",
    # Storage
    "Storage",
    "LocalStorage",
    # Scheduling
    "SimpleScheduler",
    "SequentialScheduler",
    "SchedulerConfig",
    # Tracing
    "HistoryStore",
    "TickRecord",
]
