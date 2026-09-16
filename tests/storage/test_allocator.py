"""Tests for reserved entity registration in EntityAllocator."""

from agentecs.models.identity import EntityId, SystemEntity
from agentecs.services.storage.allocator import EntityAllocator


def test_reserved_entities_are_alive_from_construction() -> None:
    """WORLD, CLOCK and SCHEDULER are allocator-alive with no allocation call.

    Why: singleton components are written to these entities, and every read path
    filters on is_alive. Without registration they are invisible to query().
    """
    allocator = EntityAllocator()

    for reserved in SystemEntity.RESERVED_ENTITIES:
        assert allocator.is_alive(reserved)


def test_unnamed_reserved_indices_are_not_alive() -> None:
    """Only the named members are registered, not the whole reserved range.

    Why: _RESERVED_COUNT is the allocation floor, not a set to iterate. Seeding all
    of it would make 997 entities nobody created report alive.
    """
    allocator = EntityAllocator()
    named = {reserved.index for reserved in SystemEntity.RESERVED_ENTITIES}

    unnamed = [
        EntityId(shard=0, index=index, generation=0)
        for index in (3, 500, SystemEntity._RESERVED_COUNT - 1)
        if index not in named
    ]

    assert all(not allocator.is_alive(entity) for entity in unnamed)


def test_allocation_does_not_collide_with_reserved_indices() -> None:
    """The first allocated index still clears the reserved range."""
    allocator = EntityAllocator()

    entity = allocator.allocate()

    assert entity.index >= SystemEntity._RESERVED_COUNT


def test_reserved_entities_are_not_registered_on_other_shards() -> None:
    """Reserved entities belong to shard 0 only.

    Why: they are declared at shard 0, so a non-zero shard registering them would
    claim liveness for identifiers it does not own.
    """
    allocator = EntityAllocator(shard=1)

    for reserved in SystemEntity.RESERVED_ENTITIES:
        assert not allocator.is_alive(reserved)


# State export and import


def test_load_round_trips_liveness() -> None:
    """load(dump()) reports the same liveness for live, destroyed and reserved entities.

    Why: the generation map is the sole liveness source. A snapshot that drops it makes
    every restored entity report dead, which is the bug this closes (#71).
    """
    allocator = EntityAllocator()
    live = allocator.allocate()
    dead = allocator.allocate()
    allocator.deallocate(dead)

    restored = EntityAllocator.load(allocator.dump())

    assert restored.is_alive(live)
    assert not restored.is_alive(dead)
    for reserved in SystemEntity.RESERVED_ENTITIES:
        assert restored.is_alive(reserved)


def test_dumped_state_is_isolated_from_later_mutation() -> None:
    """A dumped state is unaffected by allocation or deallocation afterwards.

    Why: AllocatorState is frozen, but that protects the field bindings, not the list and
    dict behind them. Without copies the state is a live view of the allocator.
    """
    allocator = EntityAllocator()
    entity = allocator.allocate()
    state = allocator.dump()

    allocator.allocate()
    allocator.deallocate(entity)

    restored = EntityAllocator.load(state)

    assert restored.is_alive(entity)
    assert restored.dump().next_index == state.next_index


def test_loaded_allocator_adopts_the_state_shard() -> None:
    """A loaded allocator is described by the state, not by how it was constructed."""
    source = EntityAllocator(shard=1)

    restored = EntityAllocator.load(source.dump())

    assert restored.dump().shard == 1
