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
    Diffable,
    EntityId,
    Interpolatable,
    Mergeable,
    NonMergeableHandling,
    NonSplittableHandling,
    Query,
    Reducible,
    Splittable,
    SystemEntity,
    SystemMode,
    component,
    merge_components,
    reduce_components,
    system,
)

# Scheduling
from agentecs.scheduling import (
    MergeStrategy,
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
    ReadOnlyAccess,
    ScopedAccess,
    SystemResult,
    World,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "EntityId",
    "SystemEntity",
    "component",
    "system",
    "SystemMode",
    "Query",
    "Mergeable",
    "Splittable",
    "Reducible",
    "Diffable",
    "Interpolatable",
    "NonMergeableHandling",
    "NonSplittableHandling",
    "merge_components",
    "reduce_components",
    # World
    "World",
    "ScopedAccess",
    "ReadOnlyAccess",
    "SystemResult",
    "AccessViolationError",
    # Storage
    "Storage",
    "LocalStorage",
    # Scheduling
    "SimpleScheduler",
    "SequentialScheduler",
    "SchedulerConfig",
    "MergeStrategy",
    # Tracing
    "HistoryStore",
    "TickRecord",
]
