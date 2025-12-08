"""Basic workflow integration tests."""

import sys
from dataclasses import dataclass

sys.path.insert(0, "src")

from agentecs import ScopedAccess, World, component, system


@component
@dataclass(slots=True)
class TestPosition:
    x: float
    y: float


@component
@dataclass(slots=True)
class TestVelocity:
    dx: float
    dy: float


def test_spawn_and_get():
    """Test basic ECS operations: spawn entity and get component."""
    world = World()
    entity = world.spawn(TestPosition(1.0, 2.0))

    pos = world.get(entity, TestPosition)
    assert pos is not None
    assert pos.x == 1.0
    assert pos.y == 2.0


def test_system_execution():
    """Test basic ECS operations: system execution."""

    @system(reads=(TestPosition, TestVelocity), writes=(TestPosition,))
    def movement(world: ScopedAccess) -> None:
        for entity, pos, vel in world(TestPosition, TestVelocity):
            world[entity, TestPosition] = TestPosition(
                pos.x + vel.dx,
                pos.y + vel.dy,
            )

    world = World()
    entity = world.spawn(TestPosition(0, 0), TestVelocity(1, 2))
    world.register_system(movement)

    world.tick()

    pos = world.get(entity, TestPosition)
    assert pos is not None
    assert pos.x == 1.0
    assert pos.y == 2.0


def test_dict_style_access():
    """Test basic ECS operations: dictionary-style access."""

    @system(reads=(TestPosition,), writes=(TestPosition,))
    def modify(world: ScopedAccess) -> None:
        for entity in world(TestPosition).entities():
            old = world[entity, TestPosition]
            world[entity, TestPosition] = TestPosition(old.x + 1, old.y)

    world = World()
    entity = world.spawn(TestPosition(5, 5))
    world.register_system(modify)
    world.tick()

    pos = world.get(entity, TestPosition)
    assert pos.x == 6


def test_membership_check():
    """Test basic ECS operations: membership check."""

    @system(reads=(TestPosition, TestVelocity), writes=())
    def check(world: ScopedAccess) -> None:
        for _ in world(TestPosition).entities():
            # entities() yields EntityId directly
            pass

    world = World()
    world.spawn(TestPosition(0, 0), TestVelocity(1, 1))
    world.register_system(check)
    world.tick()  # Should not raise


# TODO: Test access violation detection
# TODO: Test parallel system execution via Scheduler
# TODO: Test entity handle usage
# TODO: Test system return value normalization
