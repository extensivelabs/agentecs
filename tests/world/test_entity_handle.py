"""Tests for EntityHandle wrapper."""

from dataclasses import dataclass

import pytest

from agentecs import ScopedAccess, World, component, system


@component
@dataclass
class Position:
    x: float
    y: float


@component
@dataclass
class Velocity:
    dx: float
    dy: float


@pytest.fixture
def world():
    return World()


def test_entity_handle_getitem(world):
    """EntityHandle[Type] returns component or None."""
    entity = world.spawn(Position(1.0, 2.0))
    result = None

    @system(reads=(Position,), writes=())
    def read_via_handle(access: ScopedAccess) -> None:
        nonlocal result
        handle = access.entity(entity)
        result = handle[Position]

    world.register_system(read_via_handle)
    world.tick()

    assert result is not None
    assert result.x == 1.0
    assert result.y == 2.0


def test_entity_handle_setitem(world):
    """EntityHandle[Type] = value sets component."""
    entity = world.spawn(Position(0.0, 0.0))

    @system(reads=(Position,), writes=(Position,))
    def write_via_handle(access: ScopedAccess) -> None:
        handle = access.entity(entity)
        handle[Position] = Position(5.0, 10.0)

    world.register_system(write_via_handle)
    world.tick()

    pos = world.get_copy(entity, Position)
    assert pos is not None
    assert pos.x == 5.0
    assert pos.y == 10.0


def test_entity_handle_delitem(world):
    """Del EntityHandle[Type] removes component."""
    entity = world.spawn(Position(1.0, 2.0), Velocity(1.0, 1.0))

    @system(reads=(Position, Velocity), writes=(Velocity,))
    def remove_via_handle(access: ScopedAccess) -> None:
        handle = access.entity(entity)
        del handle[Velocity]

    world.register_system(remove_via_handle)
    world.tick()

    assert world.get_copy(entity, Position) is not None
    assert world.get_copy(entity, Velocity) is None


def test_entity_handle_contains(world):
    """Type in EntityHandle checks component presence."""
    entity = world.spawn(Position(1.0, 2.0))
    has_pos = None
    has_vel = None

    @system(reads=(Position, Velocity), writes=())
    def check_via_handle(access: ScopedAccess) -> None:
        nonlocal has_pos, has_vel
        handle = access.entity(entity)
        has_pos = Position in handle
        has_vel = Velocity in handle

    world.register_system(check_via_handle)
    world.tick()

    assert has_pos is True
    assert has_vel is False


def test_entity_handle_id_property(world):
    """EntityHandle.id returns the entity ID."""
    entity = world.spawn(Position(1.0, 2.0))
    handle_id = None

    @system(reads=(Position,), writes=())
    def get_handle_id(access: ScopedAccess) -> None:
        nonlocal handle_id
        handle = access.entity(entity)
        handle_id = handle.id

    world.register_system(get_handle_id)
    world.tick()

    assert handle_id == entity
