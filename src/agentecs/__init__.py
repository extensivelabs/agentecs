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

# Core primitives
from agentecs.core import (
    Combinable,
    Copy,
    EntityId,
    Query,
    Splittable,
    SystemEntity,
    SystemMode,
    component,
    system,
)

# Scheduling
from agentecs.scheduling import (
    SchedulerConfig,
    SequentialScheduler,
    SimpleScheduler,
)

# Storage
from agentecs.storage import (
    LocalStorage,
    Storage,
)

# Tracing (optional)
from agentecs.tracing import (
    HistoryStore,
    TickRecord,
)

# World and access
from agentecs.world import (
    AccessViolationError,
    MutationOp,
    OpKind,
    ReadOnlyAccess,
    ScopedAccess,
    SystemResult,
    World,
)

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
