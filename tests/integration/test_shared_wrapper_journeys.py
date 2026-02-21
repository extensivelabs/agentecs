"""Journey tests for Shared wrapper behavior and copy semantics."""

from dataclasses import dataclass
from typing import cast

import pytest

from agentecs import ScopedAccess, World, component, system
from agentecs.core.component import Shared
from agentecs.storage.local import LocalStorage


@component
@dataclass(slots=True)
class SharedCounter:
    value: int


def _raw_counter(storage: LocalStorage, entity) -> SharedCounter:
    counter = storage.get_component(entity, SharedCounter, copy=False)
    assert counter is not None
    return counter


def test_same_shared_object_across_entities_keeps_one_underlying_instance() -> None:
    """Guards identity sharing: same object should map to one shared storage slot."""
    world = World()
    storage = cast(LocalStorage, world._storage)

    counter = SharedCounter(1)
    entity_a = world.spawn(Shared(counter))
    entity_b = world.spawn(Shared(counter))
    entity_x = world.spawn()
    world.set(entity_x, Shared(counter))

    raw_a = _raw_counter(storage, entity_a)
    raw_b = _raw_counter(storage, entity_b)
    raw_x = _raw_counter(storage, entity_x)

    assert raw_a is raw_b is raw_x
    assert len(storage._shared_components) == 1


def test_different_objects_with_same_value_do_not_share_instance() -> None:
    """Prevents value-based aliasing: equal payloads with different ids must not co-share."""
    world = World()
    storage = cast(LocalStorage, world._storage)

    entity_a = world.spawn(Shared(SharedCounter(7)))
    entity_b = world.spawn(Shared(SharedCounter(7)))

    raw_a = _raw_counter(storage, entity_a)
    raw_b = _raw_counter(storage, entity_b)

    assert raw_a is not raw_b
    assert len(storage._shared_components) == 2


@pytest.mark.xfail(
    reason=(
        "World reads return deep copies, so wrapping a read copy does not keep shared identity yet"
    ),
    strict=False,
)
def test_wrapping_world_get_copy_reuses_existing_shared_group() -> None:
    """Captures desired UX: wrapping a world read copy should preserve shared grouping."""
    world = World()
    storage = cast(LocalStorage, world._storage)

    counter = SharedCounter(3)
    entity_a = world.spawn(Shared(counter))
    entity_b = world.spawn(Shared(counter))
    entity_x = world.spawn()

    copied_counter = world.get_copy(entity_a, SharedCounter)
    assert copied_counter is not None

    world.set(entity_x, Shared(copied_counter))

    raw_a = _raw_counter(storage, entity_a)
    raw_b = _raw_counter(storage, entity_b)
    raw_x = _raw_counter(storage, entity_x)

    assert raw_a is raw_b is raw_x
    assert len(storage._shared_components) == 1


@pytest.mark.xfail(
    reason=(
        "Query reads return deep copies, so wrapping a queried copy cannot reuse shared group yet"
    ),
    strict=False,
)
def test_wrapping_query_copy_reuses_existing_shared_group() -> None:
    """Captures desired UX: wrapping a query result should preserve shared grouping."""
    world = World()
    storage = cast(LocalStorage, world._storage)

    counter = SharedCounter(4)
    entity_a = world.spawn(Shared(counter))
    entity_b = world.spawn(Shared(counter))
    entity_x = world.spawn()

    queried_counter = None
    for entity, counter in world.query_copies(SharedCounter):
        if entity == entity_a:
            queried_counter = counter
            break

    assert queried_counter is not None

    world.set(entity_x, Shared(queried_counter))

    raw_a = _raw_counter(storage, entity_a)
    raw_b = _raw_counter(storage, entity_b)
    raw_x = _raw_counter(storage, entity_x)

    assert raw_a is raw_b is raw_x
    assert len(storage._shared_components) == 1


@pytest.mark.xfail(
    reason=(
        "ScopedAccess reads return deep copies, so wrapping read values "
        "cannot preserve shared group yet"
    ),
    strict=False,
)
def test_wrapping_scoped_read_copy_reuses_existing_shared_group() -> None:
    """Captures desired UX: wrapping system-read copies should preserve shared grouping."""
    world = World()
    storage = cast(LocalStorage, world._storage)

    counter = SharedCounter(9)
    source = world.spawn(Shared(counter))
    buddy = world.spawn(Shared(counter))
    target = world.spawn()

    @system(reads=(SharedCounter,), writes=(SharedCounter,))
    def move_copy_into_shared(access: ScopedAccess) -> None:
        counter_copy = access[source, SharedCounter]
        access[target, SharedCounter] = Shared(counter_copy)

    world.register_system(move_copy_into_shared)
    world.tick()

    raw_source = _raw_counter(storage, source)
    raw_buddy = _raw_counter(storage, buddy)
    raw_target = _raw_counter(storage, target)

    assert raw_source is raw_buddy is raw_target
    assert len(storage._shared_components) == 1


def test_shared_slot_garbage_collected_after_last_reference_removed() -> None:
    """Ensures shared storage is reclaimed only after the final entity reference is gone."""
    storage = LocalStorage()

    entity_a = storage.create_entity()
    entity_b = storage.create_entity()
    entity_x = storage.create_entity()

    counter = SharedCounter(11)
    for entity in (entity_a, entity_b, entity_x):
        storage.set_component(entity, Shared(counter))

    instance_id = storage._shared_refs[(entity_a, SharedCounter)]
    assert instance_id in storage._shared_components

    storage.remove_component(entity_a, SharedCounter)
    assert instance_id in storage._shared_components

    storage.remove_component(entity_b, SharedCounter)
    assert instance_id in storage._shared_components

    storage.remove_component(entity_x, SharedCounter)
    assert instance_id not in storage._shared_components


def test_replacing_shared_on_one_entity_detaches_only_that_entity() -> None:
    """Verifies overwrite isolation: replacing one entity's shared ref leaves others intact."""
    storage = LocalStorage()

    entity_a = storage.create_entity()
    entity_b = storage.create_entity()

    first = SharedCounter(1)
    second = SharedCounter(2)

    storage.set_component(entity_a, Shared(first))
    storage.set_component(entity_b, Shared(first))
    storage.set_component(entity_a, Shared(second))

    raw_a = _raw_counter(storage, entity_a)
    raw_b = _raw_counter(storage, entity_b)

    assert raw_a is second
    assert raw_b is first
    assert raw_a is not raw_b
    assert len(storage._shared_components) == 2
