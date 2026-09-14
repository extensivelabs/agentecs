"""Protocol for the read-only world view handed to PURE and READONLY systems."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, TypeVar

from agentecs.models.identity import EntityId

T = TypeVar("T")


class ReadOnlyAccess(Protocol):
    """Read-only world view for PURE and READONLY systems."""

    def query(self, *component_types: type) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Query entities by component types."""
        ...

    def get(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get a component from an entity."""
        ...

    def has(self, entity: EntityId, component_type: type) -> bool:
        """Check if entity has a component."""
        ...

    def singleton(self, component_type: type[T]) -> T:
        """Get a singleton component."""
        ...

    def entities(self) -> Iterator[EntityId]:
        """Iterate all entities."""
        ...
