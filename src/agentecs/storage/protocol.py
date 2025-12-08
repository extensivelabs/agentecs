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

    def get_component(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get component from entity."""
        ...

    def set_component(self, entity: EntityId, component: Any) -> None:
        """Set/update component on entity."""
        ...

    def remove_component(self, entity: EntityId, component_type: type) -> bool:
        """Remove component from entity. Returns True if existed."""
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
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components."""
        ...

    def query_single(self, component_type: type[T]) -> Iterator[tuple[EntityId, T]]:
        """Optimized single-component query."""
        ...

    def apply_updates(
        self,
        updates: dict[EntityId, dict[type, Any]],
        inserts: dict[EntityId, list[Any]],
        removes: dict[EntityId, list[type]],
        destroys: list[EntityId],
    ) -> list[EntityId]:
        """Apply batched changes. Returns list of newly created entity IDs."""
        ...

    def snapshot(self) -> bytes:
        """Serialize entire storage state."""
        ...

    def restore(self, data: bytes) -> None:
        """Restore from snapshot."""
        ...

    # Async variants for distributed/remote storage backends

    async def get_component_async(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get component from entity (async variant for remote storage)."""
        ...

    def query_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components (async variant).

        Note: This method returns an async iterator. Implementations typically use
        async generators (async def with yield) to implement this protocol method.
        """
        ...

    async def apply_updates_async(
        self,
        updates: dict[EntityId, dict[type, Any]],
        inserts: dict[EntityId, list[Any]],
        removes: dict[EntityId, list[type]],
        destroys: list[EntityId],
    ) -> list[EntityId]:
        """Apply batched changes asynchronously. Returns list of newly created entity IDs."""
        ...
