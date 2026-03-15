"""Storage protocol for swappable backends.

The storage layer abstracts component storage, enabling:
- Local in-memory (default)
- Distributed/sharded (future)
- Persistent (future)

Usage:
    storage = LocalStorage()
    world = World(storage=storage)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol, TypeVar

from agentecs.core.identity import EntityId

T = TypeVar("T")


class Storage(Protocol):
    """Abstract storage interface. Implementations handle actual data."""

    def create_entity(self) -> EntityId:
        """Allocate new entity."""
        ...

    def destroy_entity(self, entity: EntityId) -> None:
        """Remove entity and all its components."""
        ...

    def entity_exists(self, entity: EntityId) -> bool:
        """Check if entity is alive."""
        ...

    def all_entities(self) -> Iterator[EntityId]:
        """Iterate all living entities."""
        ...

    def get_component(
        self, entity: EntityId, component_type: type[T], copy: bool = True
    ) -> T | None:
        """Get component from entity."""
        ...

    def set_component(self, entity: EntityId, component: Any) -> None:
        """Set/update component on entity."""
        ...

    def remove_component(self, entity: EntityId, component_type: type) -> bool:
        """Remove component from entity. Returns True if existed."""
        ...

    def remove_component_from_all(self, component_type: type) -> None:
        """Remove a component type from all entities."""
        ...

    def has_component(self, entity: EntityId, component_type: type) -> bool:
        """Check if entity has component."""
        ...

    def get_component_types(self, entity: EntityId) -> frozenset[type]:
        """Get all component types on entity."""
        ...

    def query(
        self,
        *component_types: type,
        copy: bool = True,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components."""
        ...

    def query_single(
        self, component_type: type[T], copy: bool = True
    ) -> Iterator[tuple[EntityId, T]]:
        """Optimized single-component query."""
        ...

    def snapshot(self) -> bytes:
        """Serialize entire storage state."""
        ...

    def restore(self, data: bytes) -> None:
        """Restore from snapshot."""
        ...

    # Async variants for distributed/remote storage backends

    async def get_component_async(
        self, entity: EntityId, component_type: type[T], copy: bool = True
    ) -> T | None:
        """Get component from entity (async variant for remote storage)."""
        ...

    def query_async(
        self,
        *component_types: type,
        copy: bool = True,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]] | Any:
        """Find entities with all specified components (async variant).

        Returns an async iterator (typically via async generator implementation).
        The `| Any` allows both async generators and awaitable-returning implementations.
        """
        ...
