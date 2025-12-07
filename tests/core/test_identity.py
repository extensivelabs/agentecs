"""Tests for entity identity system.

Critical Invariants:
- Generation increments on recycle
- Stale handles are detected
- Shard boundaries are enforced
- Reserved IDs are protected
"""

import pytest

from agentecs.core.identity import SystemEntity
from agentecs.storage.allocator import EntityAllocator


@pytest.fixture
def allocator():
    """Create an EntityAllocator for shard 0."""
    return EntityAllocator(shard=0)


@pytest.fixture
def allocator_shard1():
    """Create an EntityAllocator for shard 1."""
    return EntityAllocator(shard=1)


# Entity generation tests - critical for safety


def test_generation_increments_on_recycle(allocator):
    """CRITICAL: Recycled entity must have generation+1.

    Why: Prevents use-after-free bugs where stale handle references wrong entity.
    """
    # Allocate and deallocate
    entity1 = allocator.allocate()
    assert entity1.generation == 0

    allocator.deallocate(entity1)

    # Reallocate same index
    entity2 = allocator.allocate()
    assert entity2.index == entity1.index, "Should reuse same index"
    assert entity2.generation == 1, "INVARIANT: generation must increment"


def test_stale_handle_detection(allocator):
    """CRITICAL: is_alive() returns False for stale handles.

    Why: Prevents accessing recycled entity with old generation.
    """
    entity_old = allocator.allocate()
    allocator.deallocate(entity_old)

    # After deallocation, old handle is stale
    assert not allocator.is_alive(entity_old), "Old generation should be stale"

    # New allocation has incremented generation
    entity_new = allocator.allocate()
    assert allocator.is_alive(entity_new), "New generation should be alive"
    assert entity_new.index == entity_old.index
    assert entity_new.generation == entity_old.generation + 1


# Shard boundary tests - critical for distributed correctness


def test_cannot_deallocate_from_wrong_shard(allocator, allocator_shard1):
    """CRITICAL: Entity from shard N cannot be deallocated on shard M.

    Why: Prevents cross-shard data corruption in distributed setting.
    """
    entity_shard1 = allocator_shard1.allocate()

    with pytest.raises(ValueError, match="Cannot deallocate entity from shard"):
        allocator.deallocate(entity_shard1)


def test_cross_shard_liveness_returns_false(allocator, allocator_shard1):
    """is_alive() returns False for entities from other shards.

    Note: This will need updating when cross-shard queries are implemented.
    """
    entity_shard1 = allocator_shard1.allocate()

    # Shard 0 allocator doesn't know about shard 1 entities
    assert not allocator.is_alive(entity_shard1)


# Reserved entity ID tests - prevents collision with singletons


def test_allocated_entities_skip_reserved_range(allocator):
    """CRITICAL: First allocated entity index >= _RESERVED_COUNT.

    Why: Prevents collision with WellKnownEntity singletons.
    """
    entity = allocator.allocate()

    assert entity.index >= SystemEntity._RESERVED_COUNT, (
        f"Entity index {entity.index} collides with reserved range "
        f"[0, {SystemEntity._RESERVED_COUNT})"
    )


# EntityId property tests skipped - testing Python dataclass behavior
