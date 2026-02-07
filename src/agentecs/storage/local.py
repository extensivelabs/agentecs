"""Local in-memory storage implementation.

Simple dict-based storage suitable for single-process use and testing.
Not optimized - future versions should use archetypal storage.

Usage:
    storage = LocalStorage()
    world = World(storage=storage)
"""

from __future__ import annotations

import copy as cp
import pickle  # nosec B403 - Used only for local testing/prototyping, not production
from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar, cast
from uuid import UUID

from agentecs import Copy
from agentecs.core import Shared
from agentecs.core.component.wrapper import WrappedComponent
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

        self._shared_refs: dict[tuple[EntityId, type], UUID] = {}
        self._shared_components: dict[UUID, Any] = {}
        self._shared_type_ref: dict[type, UUID] = {}
        """The shared types are stored as follows:
        _shared_refs maps entities to UUIDs of instances of shared components.
        _shared_components maps those UUIDs to the actual shared component instances.
        _shared_type_refs maps those components that are shared by type to their shared UUIDs.
        """

    def _is_shared_type(self, component_type: type) -> bool:
        """Check if component type is marked as shared via decorator."""
        meta = getattr(component_type, "__component_meta__", None)
        return meta is not None and getattr(meta, "shared", False)

    def _is_wrapped_component(self, component: Any) -> type[WrappedComponent[Any]] | None:
        """Check if a component instance is wrapped e.g. Shared and return the wrapper type."""
        if isinstance(component, WrappedComponent):
            if isinstance(component, Shared):
                return Shared
            else:
                # Future wrapper types can be checked here
                pass
        return None

    def _is_shared_type_or_instance(self, component: Any) -> bool:
        """Check if a component instance is shared (either wrapper or type)."""
        return self._is_wrapped_component(component) is Shared or self._is_shared_type(
            type(component)
        )

    def _is_shared(self, entity: EntityId, component_type: type) -> bool:
        """Check if a component is shared (either per-instance or per-type)."""
        # Per-instance sharing (via Shared() wrapper)
        if (entity, component_type) in self._shared_refs:
            return True
        # Per-type sharing (via @component(shared=True))
        return self._is_shared_type(component_type)

    def _return_shared_id(self, entity: EntityId, component_type: type) -> UUID | None:
        """Check if this entity's component is shared and return id or None."""
        return self._shared_refs.get((entity, component_type))

    def _get_component_raw(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get component without copy (internal use). Unwraps shared wrappers."""
        if shared_id := self._return_shared_id(entity, component_type):
            component = self._shared_components.get(shared_id)
            if isinstance(component, WrappedComponent):
                return cast(T, component.unwrap())
            return cast(T, component)
        return self._components.get(entity, {}).get(component_type)

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

    def get_component(
        self, entity: EntityId, component_type: type[T], copy: bool = True
    ) -> Copy[T] | T | None:
        """Get a component from an entity.

        Args:
            entity: Entity to query.
            component_type: Type of component to retrieve.
            copy: Whether to return a copy of the component (default True).

        Returns:
            Component instance or None if not present.
        """
        if entity not in self._components:
            return None
        component = self._get_component_raw(entity, component_type)
        if component is None:
            return None
        return cp.deepcopy(component) if copy else component

    def set_component(self, entity: EntityId, component: Any) -> None:
        """Set or update a component on an entity.

        Shared components are added as follows:
        - If the component is wrapped in Shared, it is stored
          as a shared instance and mapped to the entity.
        - If the component's type is decorated as shared, we wrap
          it as needed and store it as shared type, and wrapped instance.

        Args:
            entity: Entity to modify.
            component: Component instance to set (type inferred).
        """
        if entity not in self._components:
            self._components[entity] = {}

        if self._is_shared_type_or_instance(component):
            if self._is_wrapped_component(component) is Shared:
                shared_id = component.ref_id
                # Set the shared component instance if not already stored
                self._shared_components[shared_id] = component
                # Assign the shared reference ID to this entity's component slot
                self._shared_refs[(entity, component.component_type)] = shared_id
                # Ensure prior component type is cleared if it exists and is different
                if component.component_type in self._components[entity]:
                    del self._components[entity][component.component_type]
            else:
                # Shared by type.
                if shared_id := self._shared_type_ref.get(type(component)):
                    # If this type is already shared, just reference it
                    self._shared_refs[(entity, type(component))] = shared_id
                    # Wrap the component in the shared wrapper for storage
                    wrapper = Shared(component)
                    wrapper._ref.instance_id = shared_id
                    # Assign or update
                    self._shared_components[shared_id] = component
                else:
                    # First time seeing this type. Wrap it.
                    wrapper = Shared(component)
                    shared_id = wrapper.ref_id
                    self._shared_type_ref[type(component)] = shared_id
                    self._shared_refs[(entity, type(component))] = shared_id
                    self._shared_components[shared_id] = component
        else:
            # Regular component - store directly
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
        if self._is_shared(entity, component_type):
            # Remove shared instance reference for this entity
            if (entity, component_type) in self._shared_refs:
                del self._shared_refs[(entity, component_type)]
            return True
        if component_type in self._components[entity]:
            del self._components[entity][component_type]
            return True
        return False

    def remove_component_from_all(self, component_type: type) -> None:
        """Remove a component type from all entities.

        This completely removes shared components.

        Args:
            component_type: Type of component to remove from all entities.
        """
        # Remove shared type reference if it exists
        if component_type in self._shared_type_ref:
            shared_id = self._shared_type_ref[component_type]
            del self._shared_type_ref[component_type]

        # Remove all shared instance references for this component type
        to_remove = [key for key, sid in self._shared_refs.items() if sid == shared_id]
        for key in to_remove:
            del self._shared_refs[key]
        if shared_id in self._shared_components:
            del self._shared_components[shared_id]

        # Remove from all entities
        for entity in list(self._components.keys()):
            self.remove_component(entity, component_type)

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

        if self._is_shared(entity, component_type):
            return True

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
        types = set(self._components[entity].keys())
        # Add shared types
        for (e, t), _ in self._shared_refs.items():
            if e == entity:
                types.add(t)
        return frozenset(types)

    def query(
        self,
        *component_types: type,
        copy: bool = True,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components.

        O(n) scan - archetypal storage would be O(matched).

        Args:
            *component_types: Component types to query for.
            copy: Whether to return copies of components (default True).

        Yields:
            Tuples of (entity, (component1, component2, ...)) for each match.
        """
        type_set = set(component_types)
        for entity, components in self._components.items():
            if not self._allocator.is_alive(entity):
                continue
            entity_types = set(components.keys())
            for (e, t), _ in self._shared_refs.items():
                if e == entity:
                    entity_types.add(t)
            if type_set.issubset(entity_types):
                if copy:
                    result = tuple(
                        cp.deepcopy(self._get_component_raw(entity, t)) for t in component_types
                    )
                else:
                    result = tuple(self._get_component_raw(entity, t) for t in component_types)
                yield entity, result

    def query_single(
        self, component_type: type[T], copy: bool = True
    ) -> Iterator[tuple[EntityId, T]]:
        """Optimized single-component query.

        Args:
            component_type: Component type to query for.
            copy: Whether to return copies of components (default True).

        Yields:
            Tuples of (entity, component) for each match.
        """
        # Since this is local, no need to optimize here.
        iterator = self.query(component_type, copy=copy)
        for entity, components in iterator:
            yield entity, components[0]

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
                "shared_refs": self._shared_refs,
                "shared_components": self._shared_components,
                "shared_type_ref": self._shared_type_ref,
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
        self._shared_refs = state["shared_refs"]
        self._shared_components = state["shared_components"]
        self._shared_type_ref = state["shared_type_ref"]

    # Async variants - for LocalStorage these just wrap sync methods
    # Future distributed storage backends can implement truly async versions

    async def get_component_async(
        self, entity: EntityId, component_type: type[T], copy: bool = True
    ) -> T | None:
        """Get component from entity (async wrapper for sync implementation).

        Args:
            entity: Entity to query.
            component_type: Type of component to retrieve.
            copy: Whether to return a copy of the component (default True).

        Returns:
            Component instance or None if not present.
        """
        return self.get_component(entity, component_type, copy)

    async def query_async(
        self, *component_types: type, copy: bool = True
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Find entities with all specified components (async wrapper).

        Args:
            *component_types: Component types to query for.
            copy: Whether to return copies of components (default True).

        Yields:
            Tuples of (entity, (component1, component2, ...)) for each match.
        """
        for entity, components in self.query(*component_types, copy=copy):
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
