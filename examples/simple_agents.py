"""Basic AgentECS usage example.

Demonstrates:
- Component definition
- System definition with access control
- World creation and entity spawning
- System execution (both sync and async)
"""

import asyncio
from dataclasses import dataclass

from agentecs import ScopedAccess, World, component, system


@component
@dataclass(slots=True)
class Position:
    x: float
    y: float

    def __merge__(self, other: "Position") -> "Position":
        return Position(x=(self.x + other.x) / 2, y=(self.y + other.y) / 2)


@component
@dataclass(slots=True)
class Velocity:
    dx: float
    dy: float


@component
@dataclass(slots=True)
class AgentTag:
    """Marker component identifying AI agents."""

    name: str


@component
@dataclass(slots=True)
class Health:
    hp: int
    max_hp: int


@system(
    reads=(
        Position,
        Velocity,
    ),
    writes=(Position,),
)
def movement_system(world: ScopedAccess) -> None:
    """Move entities based on velocity."""
    for entity, pos, vel in world(Position, Velocity):
        world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)


@system(reads=(Position, Velocity), writes=(Velocity, Position))
def collision_system(world: ScopedAccess) -> None:
    """Check for collisions and reverse velocity if needed."""
    position_cache = {}
    collision_cache = set()
    for entity, pos in world(Position):
        pos_key = (round(pos.x), round(pos.y))
        if pos_key in position_cache:
            # Collision detected, reverse velocity
            print(f"  [Collision] Entity {entity.index} collided at {pos_key}")
            collision_cache.add(pos_key)
        else:
            position_cache[pos_key] = entity
    # Reverse velocity for colliding entities
    for collision in collision_cache:
        for entity, pos, vel in world(Position, Velocity):
            pos_key = (round(pos.x), round(pos.y))
            if pos_key == collision:
                # Move entity back to previous position and reverse velocity
                world[entity, Position] = Position(pos.x - vel.dx, pos.y - vel.dy)
                world[entity, Velocity] = Velocity(-vel.dx, -vel.dy)
                print(f"    Reversing velocity of Entity {entity.index}")


@system(reads=(Position, AgentTag), writes=())
def print_agents_system(world: ScopedAccess) -> None:
    """Print agent positions (read-only observer)."""
    for _, pos, agent in world(Position, AgentTag):
        print(f"Agent '{agent.name}' at ({pos.x}, {pos.y})")


@system.dev()
def debug_system(world: ScopedAccess) -> None:
    """Dev mode: inspect everything."""
    print("=== World State ===")
    for entity in world:
        print(f"  Entity {entity}:")
        # Dev mode can access any component
        if world.has(entity, Position):
            pos = world[entity, Position]
            print(f"    Position: ({pos.x}, {pos.y})")
        if world.has(entity, Velocity):
            vel = world[entity, Velocity]
            print(f"    Velocity: ({vel.dx}, {vel.dy})")
        if world.has(entity, AgentTag):
            tag = world[entity, AgentTag]
            print(f"    AgentTag: {tag.name}")


# Example async system
@system(reads=(Position, AgentTag), writes=())
async def async_observer_system(world: ScopedAccess) -> None:
    """Example async system (could do async I/O, API calls, etc.)."""
    await asyncio.sleep(0.001)  # Simulate async operation
    agent_count = sum(1 for _ in world(Position, AgentTag))
    print(f"  [Async Observer] Found {agent_count} agents")


async def main_async():
    """Async main demonstrating async/await usage."""
    # Create world
    world = World()

    # Spawn some agents
    world.spawn(
        Position(0, 5),
        Velocity(1, 0),
        AgentTag(name="Alice"),
    )

    world.spawn(
        Position(10, 5),
        Velocity(-1, 0),
        AgentTag(name="Bob"),
    )

    # Static entity (no velocity)
    world.spawn(Position(15, 5))

    # Register systems (mix of sync and async)
    world.register_system(movement_system)
    world.register_system(print_agents_system)
    world.register_system(async_observer_system)
    world.register_system(collision_system)
    # world.register_system(debug_system)

    # Run a few ticks using async API
    for tick in range(20):
        print(f"\n--- Tick {tick} ---")
        await world.tick_async()

    print("Done.")


def main():
    """Sync wrapper for main_async (for simple script usage)."""
    asyncio.run(main_async())


if __name__ == "__main__":
    # Can call either:
    # main()  # Sync wrapper
    # asyncio.run(main_async())  # Direct async
    main()
