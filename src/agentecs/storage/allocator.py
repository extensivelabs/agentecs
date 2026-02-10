"""Entity allocation service.

EntityAllocator is a stateful service that manages entity ID lifecycle.
"""

from __future__ import annotations

from agentecs.core.identity import EntityId, SystemEntity


class EntityAllocator:
    """Allocates entity IDs with generation tracking for recycling.

    Maintains a free list of deallocated entity indices with incremented generations
    to safely reuse entity IDs. Starts allocation after reserved system entities.

    Args:
        shard: Shard number for this allocator (default 0 for local).
    """

    def __init__(self, shard: int = 0):
        """Initialize entity allocator for a specific shard.

        Args:
            shard: Shard number for this allocator (default 0 for local).
        """
        self._shard = shard
        self._next_index = SystemEntity._RESERVED_COUNT
        self._free_list: list[tuple[int, int]] = []  # (index, generation)
        self._generations: dict[int, int] = {}

    def allocate(self) -> EntityId:
        """Allocate new entity ID, reusing recycled slots when available.

        Prioritizes reusing freed entity IDs from the free list before allocating
        new indices. Reused IDs have incremented generation numbers.

        Returns:
            Newly allocated EntityId.
        """
        if self._free_list:
            index, gen = self._free_list.pop()
            return EntityId(shard=self._shard, index=index, generation=gen)

        index = self._next_index
        self._next_index += 1
        self._generations[index] = 0
        return EntityId(shard=self._shard, index=index, generation=0)

    def deallocate(self, entity: EntityId) -> None:
        """Return entity ID for reuse with incremented generation.

        Adds the entity's index to the free list with an incremented generation
        number, making it available for reallocation.

        Args:
            entity: Entity ID to deallocate.

        Raises:
            ValueError: If entity is from a different shard.
        """
        if entity.shard != self._shard:
            raise ValueError(
                f"Cannot deallocate entity from shard {entity.shard} on shard {self._shard}"
            )

        new_gen = entity.generation + 1
        self._generations[entity.index] = new_gen
        self._free_list.append((entity.index, new_gen))

    def is_alive(self, entity: EntityId) -> bool:
        """Check if entity ID is still valid (not recycled).

        Compares entity's generation number with the current generation for that
        index to determine if the entity is still alive or has been recycled.

        Args:
            entity: Entity ID to check.

        Returns:
            True if entity is alive, False if recycled or from different shard.
        """
        if entity.shard != self._shard:
            return False  # TODO: cross-shard liveness check
        current_gen = self._generations.get(entity.index, -1)
        return current_gen == entity.generation
