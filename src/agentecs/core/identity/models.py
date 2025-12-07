"""Entity identity models.

Usage:
    entity = EntityId(shard=0, index=42, generation=1)
    singleton = WellKnownEntity.WORLD
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityId:
    """Lightweight entity identifier with generation for safe handle reuse.

    Shard field enables future distributed scaling - each shard allocates
    indices independently within its range.
    """

    shard: int = 0  # 0 = local, >0 = remote shard
    index: int = 0
    generation: int = 0

    def __hash__(self) -> int:
        return hash((self.shard, self.index, self.generation))

    def is_local(self) -> bool:
        """Check if this entity belongs to the local shard.

        Returns:
            True if entity is on shard 0 (local), False otherwise.
        """
        return self.shard == 0


class SystemEntity:
    """Reserved entity IDs for singletons. Always on shard 0."""

    WORLD = EntityId(shard=0, index=0, generation=0)
    CLOCK = EntityId(shard=0, index=1, generation=0)
    SCHEDULER = EntityId(shard=0, index=2, generation=0)

    _RESERVED_COUNT = 1000  # First 1000 indices reserved
