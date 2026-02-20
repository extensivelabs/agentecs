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

    pos = world.get_copy(entity, TestPosition)
    assert pos is not None
    assert pos.x == 1.0
    assert pos.y == 2.0


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
