"""Local in-memory storage implementation.

Simple dict-based storage suitable for single-process use and testing.
Not optimized - future versions should use archetypal storage.

Usage:
    storage = LocalStorage()
    world = World(storage=storage)
"""

from __future__ import annotations

import pickle  # nosec B403 - Used only for local testing/prototyping, not production
from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

from agentecs.core.identity import EntityId
from agentecs.storage.allocator import EntityAllocator

T = TypeVar("T")


class LocalStorage:
    """Simple in-memory storage using nested dicts.

    Structure:
        _components[entity][component_type] = component_instance

    Not cache-efficient - for production, use archetypal storage.

    Args:
        shard: Shard number for this storage instance (default 0 for local).
    """

    def __init__(self, shard: int = 0):
        """Initialize local storage.

        Args:
            shard: Shard number for this storage instance (default 0).
        """
        self._shard = shard
        self._allocator = EntityAllocator(shard=shard)
        self._components: dict[EntityId, dict[type, Any]] = {}

    def create_entity(self) -> EntityId:
        """Create a new entity and return its ID.

        Returns:
            Newly allocated EntityId.
        """
        entity = self._allocator.allocate()
        self._components[entity] = {}
        return entity

    def destroy_entity(self, entity: EntityId) -> None:
        """Destroy an entity and remove all its components.

        Args:
            entity: Entity to destroy.
        """
        if entity in self._components:
            del self._components[entity]
            self._allocator.deallocate(entity)

    def entity_exists(self, entity: EntityId) -> bool:
        """Check if an entity exists and is alive.

        Args:
            entity: Entity to check.

        Returns:
            True if entity exists and is alive, False otherwise.
        """
        return entity in self._components and self._allocator.is_alive(entity)

    def all_entities(self) -> Iterator[EntityId]:
        """Iterate over all alive entities.

        Yields:
            EntityId for each alive entity.
        """
        for entity in self._components:
            if self._allocator.is_alive(entity):
                yield entity

    def get_component(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get a component from an entity.

        Args:
            entity: Entity to query.
            component_type: Type of component to retrieve.

        Returns:
            Component instance or None if not present.
        """
        if entity not in self._components:
            return None
        return self._components[entity].get(component_type)

    def set_component(self, entity: EntityId, component: Any) -> None:
        """Set or update a component on an entity.

        Args:
            entity: Entity to modify.
            component: Component instance to set (type inferred).
        """
        if entity not in self._components:
            self._components[entity] = {}
        self._components[entity][type(component)] = component

    def remove_component(self, entity: EntityId, component_type: type) -> bool:
        """Remove a component from an entity.

        Args:
            entity: Entity to modify.
            component_type: Type of component to remove.

        Returns:
            True if component was removed, False if not present.
        """
        if entity not in self._components:
            return False
        if component_type in self._components[entity]:
            del self._components[entity][component_type]
            return True
        return False

    def has_component(self, entity: EntityId, component_type: type) -> bool:
        """Check if an entity has a specific component type.

        Args:
            entity: Entity to check.
            component_type: Component type to look for.

        Returns:
            True if entity has component, False otherwise.
        """
        if entity not in self._components:
            return False
        return component_type in self._components[entity]

    def get_component_types(self, entity: EntityId) -> frozenset[type]:
        """Get all component types present on an entity.

        Args:
            entity: Entity to query.

        Returns:
            Frozenset of component types on entity.
        """
        if entity not in self._components:
            return frozenset()
        return frozenset(self._components[entity].keys())

    def query(
        self,
        *component_types: type,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components.

        O(n) scan - archetypal storage would be O(matched).

        Args:
            *component_types: Component types to query for.

        Yields:
            Tuples of (entity, (component1, component2, ...)) for each match.
        """
        type_set = set(component_types)
        for entity, components in self._components.items():
            if not self._allocator.is_alive(entity):
                continue
            if type_set.issubset(components.keys()):
                result = tuple(components[t] for t in component_types)
                yield entity, result

    def query_single(self, component_type: type[T]) -> Iterator[tuple[EntityId, T]]:
        """Optimized single-component query.

        Args:
            component_type: Component type to query for.

        Yields:
            Tuples of (entity, component) for each match.
        """
        for entity, components in self._components.items():
            if not self._allocator.is_alive(entity):
                continue
            if component_type in components:
                yield entity, components[component_type]

    def apply_updates(
        self,
        updates: dict[EntityId, dict[type, Any]],
        inserts: dict[EntityId, list[Any]],
        removes: dict[EntityId, list[type]],
        destroys: list[EntityId],
    ) -> list[EntityId]:
        """Apply batched changes atomically.

        Args:
            updates: Entity -> component type -> component updates.
            inserts: Entity -> list of components to insert.
            removes: Entity -> list of component types to remove.
            destroys: List of entities to destroy.

        Returns:
            List of newly created entity IDs (always empty for this implementation).
        """
        new_entities: list[EntityId] = []

        # Updates
        for entity, components in updates.items():
            for _, comp in components.items():
                self.set_component(entity, comp)

        # Inserts
        for entity, component_list in inserts.items():
            for comp in component_list:
                self.set_component(entity, comp)

        # Removes
        for entity, types in removes.items():
            for t in types:
                self.remove_component(entity, t)

        # Destroys
        for entity in destroys:
            self.destroy_entity(entity)

        return new_entities

    def snapshot(self) -> bytes:
        """Pickle entire state for serialization.

        Not efficient - use only for testing/prototyping, not production.

        Returns:
            Pickled bytes of storage state.
        """
        return pickle.dumps(
            {
                "shard": self._shard,
                "components": self._components,
                "allocator_next": self._allocator._next_index,
            }
        )

    def restore(self, data: bytes) -> None:
        """Restore from pickle snapshot.

        Args:
            data: Pickled bytes from previous snapshot() call.
        """
        state = pickle.loads(data)  # nosec B301 - Used only for local testing, not production
        self._shard = state["shard"]
        self._components = state["components"]
        self._allocator._next_index = state["allocator_next"]

    # Async variants - for LocalStorage these just wrap sync methods
    # Future distributed storage backends can implement truly async versions

    async def get_component_async(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get component from entity (async wrapper for sync implementation).

        Args:
            entity: Entity to query.
            component_type: Type of component to retrieve.

        Returns:
            Component instance or None if not present.
        """
        return self.get_component(entity, component_type)

    async def query_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components (async wrapper).

        Args:
            *component_types: Component types to query for.

        Yields:
            Tuples of (entity, (component1, component2, ...)) for each match.
        """
        for entity, components in self.query(*component_types):
            # Test
            yield entity, components

    async def apply_updates_async(
        self,
        updates: dict[EntityId, dict[type, Any]],
        inserts: dict[EntityId, list[Any]],
        removes: dict[EntityId, list[type]],
        destroys: list[EntityId],
    ) -> list[EntityId]:
        """Apply batched changes asynchronously (async wrapper).

        Args:
            updates: Entity -> component type -> component updates.
            inserts: Entity -> list of components to insert.
            removes: Entity -> list of component types to remove.
            destroys: List of entities to destroy.

        Returns:
            List of newly created entity IDs (always empty for this implementation).
        """
        return self.apply_updates(updates, inserts, removes, destroys)
