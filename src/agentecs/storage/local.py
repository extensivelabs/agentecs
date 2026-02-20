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

from agentecs import Copy
from agentecs.core import Shared
from agentecs.core.component.wrapper import WrappedComponent, get_component, get_type
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

        self._shared_refs: dict[tuple[EntityId, type], int] = {}
        self._shared_components: dict[int, Any] = {}
        self._shared_type_instance_id: dict[type, int] = {}
        """Shared component storage:
        _shared_refs: maps (entity, type) → instance_id of the shared component.
        _shared_components: maps instance_id → actual shared component instance.
        _shared_type_instance_id: maps per-type shared types → their instance_id.
        """

    def _locate_component(self, entity: EntityId, component_type: type) -> tuple[int | None, bool]:
        """Find where a component lives for an entity.

        Returns:
            (instance_id, in_regular) where instance_id is set if in shared storage,
            and in_regular is True if in _components[entity].
        """
        instance_id = self._shared_refs.get((entity, component_type))
        in_regular = component_type in self._components.get(entity, {})
        return instance_id, in_regular

    def _gc_shared(self, instance_id: int) -> None:
        """Remove shared component if no entity references it."""
        if not any(sid == instance_id for sid in self._shared_refs.values()):
            self._shared_components.pop(instance_id, None)

    def _get_component_raw(self, entity: EntityId, component_type: type[T]) -> T | None:
        """Get component without copy (internal use). Unwraps shared wrappers."""
        instance_id, _ = self._locate_component(entity, component_type)
        if instance_id is not None:
            component = self._shared_components.get(instance_id)
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
            refs = [
                (key, instance_id)
                for key, instance_id in self._shared_refs.items()
                if key[0] == entity
            ]
            for key, instance_id in refs:
                del self._shared_refs[key]
                self._gc_shared(instance_id)
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

        If the component is wrapped in Shared, it is stored as a shared instance
        and mapped to the entity via instance_id. Otherwise, stored directly.

        Args:
            entity: Entity to modify.
            component: Component instance to set (type inferred).
        """
        if entity not in self._components:
            self._components[entity] = {}

        def _set_shared(component: Shared[Any], prior_instance_id: int | None) -> None:
            """Helper to correctly set a shared component."""
            instance_id = component.ref_id
            self._shared_refs[(entity, get_type(component))] = instance_id
            self._shared_components[instance_id] = component.unwrap()
            if prior_instance_id is not None and prior_instance_id != instance_id:
                self._gc_shared(prior_instance_id)

        existing_id, _ = self._locate_component(entity, get_type(component))
        if existing_id is not None:
            if isinstance(component, Shared):
                _set_shared(component, existing_id)
            # TODO: What if shard via decorator? elif needed here?
            else:
                # Component type was previously shared but now regular - remove old shared ref
                del self._shared_refs[(entity, get_type(component))]
                self._components[entity][get_type(component)] = get_component(component)
                self._gc_shared(existing_id)
        else:
            if isinstance(component, Shared):
                if self.has_component(entity, get_type(component)):
                    self.remove_component(entity, get_type(component))
                _set_shared(component, None)

            # TODO: What if shard via decorator? elif needed here?
            else:
                self._components[entity][get_type(component)] = component

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
        instance_id, in_regular = self._locate_component(entity, component_type)
        if instance_id is not None:
            del self._shared_refs[(entity, component_type)]
            self._gc_shared(instance_id)
            return True
        if in_regular:
            del self._components[entity][component_type]
            return True
        return False

    def remove_component_from_all(self, component_type: type) -> None:
        """Remove a component type from all entities.

        This completely removes shared components.

        Args:
            component_type: Type of component to remove from all entities.
        """
        # Clean per-type shared ref
        if component_type in self._shared_type_instance_id:
            instance_id = self._shared_type_instance_id.pop(component_type)
            to_remove = [key for key, iid in self._shared_refs.items() if iid == instance_id]
            for key in to_remove:
                del self._shared_refs[key]
            self._shared_components.pop(instance_id, None)

        # Clean per-instance shared refs for this type
        to_remove_inst = [
            (key, iid) for key, iid in self._shared_refs.items() if key[1] == component_type
        ]
        for key, iid in to_remove_inst:
            del self._shared_refs[key]
            self._gc_shared(iid)

        # Clean regular storage
        for comps in self._components.values():
            comps.pop(component_type, None)

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
        instance_id, in_regular = self._locate_component(entity, component_type)
        return instance_id is not None or in_regular

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
                "shared_type_instance_id": self._shared_type_instance_id,
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
        self._shared_type_instance_id = state["shared_type_instance_id"]

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
