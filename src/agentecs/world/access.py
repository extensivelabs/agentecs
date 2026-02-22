"""World access interfaces with ergonomic magic methods.

Usage:
    # Dict-style access
    pos = world[entity, Position]
    world[entity, Position] = new_pos
    del world[entity, Velocity]

    # Query with unpacking
    for entity, pos, vel in world(Position, Velocity):
        ...

    # Membership check
    if (entity, Frozen) in world:
        ...

    # Entity handle for repeated access
    e = world.entity(entity_id)
    e[Position] = new_pos
    if Health in e:
        ...
"""

from __future__ import annotations

import copy
import warnings
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

from agentecs.core.component.wrapper import get_component, get_type
from agentecs.core.identity import EntityId, SystemEntity
from agentecs.core.system import SystemDescriptor
from agentecs.core.types import Copy
from agentecs.world.sync_runner import SyncRunner

if TYPE_CHECKING:
    from agentecs.world.result import SystemResult
    from agentecs.world.world import World

T = TypeVar("T")


class AccessViolationError(Exception):
    """Raised when system accesses undeclared components."""

    pass


class QueryResult:
    """Lazy query result with ergonomic iteration.

    Provides convenient iteration over query results with automatic unpacking
    of entity and components.

    Args:
        access: ScopedAccess instance to query from.
        component_types: Tuple of component types to query for.
    """

    def __init__(
        self,
        access: ScopedAccess,
        component_types: tuple[type, ...],
    ):
        """Initialize query result.

        Args:
            access: ScopedAccess instance to query from.
            component_types: Tuple of component types to query for.
        """
        self._access = access
        self._types = component_types

    def __iter__(self) -> Iterator[tuple[EntityId, ...]]:
        """Iterate yielding (entity, comp1, comp2, ...) with flat unpacking.

        Yields:
            Tuples of (entity_id, component1, component2, ...) for each match.
        """
        for entity, components in self._access._query_raw(*self._types):
            yield (entity, *components)

    def __len__(self) -> int:
        """Count matching entities (consumes iterator, use sparingly).

        Returns:
            Number of entities matching the query.
        """
        return sum(1 for _ in self._access._query_raw(*self._types))

    def entities(self) -> Iterator[EntityId]:
        """Iterate over just entity IDs, without components.

        Yields:
            EntityId for each matching entity.
        """
        for entity, _ in self._access._query_raw(*self._types):
            yield entity


class EntityHandle:
    """Convenient wrapper for repeated single-entity operations.

    Provides dict-style access to an entity's components with syntax like:
    e[Position] = pos, del e[Velocity], Position in e.

    Args:
        access: ScopedAccess instance.
        entity: EntityId to wrap.
    """

    def __init__(self, access: ScopedAccess, entity: EntityId):
        """Initialize entity handle.

        Args:
            access: ScopedAccess instance.
            entity: EntityId to wrap.
        """
        self._access = access
        self._entity = entity

    @property
    def id(self) -> EntityId:
        """Get the entity ID for this handle.

        Returns:
            The EntityId this handle wraps.
        """
        return self._entity

    def __getitem__(self, component_type: type[T]) -> T | None:
        """Get component from entity: e[Position] -> Position or None.

        Args:
            component_type: Component type to retrieve.

        Returns:
            Component instance or None if not present.
        """
        return self._access.get(self._entity, component_type)

    def __setitem__(self, component_type: type, value: Any) -> None:
        """Set component on entity: e[Position] = new_pos.

        Args:
            component_type: Component type (unused, inferred from value).
            value: Component instance to set.
        """
        self._access.update(self._entity, value)

    def __delitem__(self, component_type: type) -> None:
        """Remove component from entity: del e[Position].

        Args:
            component_type: Component type to remove.
        """
        self._access.remove(self._entity, component_type)

    def __contains__(self, component_type: type) -> bool:
        """Check if entity has component: Position in e.

        Args:
            component_type: Component type to check.

        Returns:
            True if entity has component, False otherwise.
        """
        return self._access.has(self._entity, component_type)


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


class ScopedAccess:
    """World access scoped to system's declared patterns with magic methods.

    Provides snapshot isolation: sees own writes immediately, others' writes
    only after tick boundary.

    Gotcha: For PURE mode systems, write methods raise AccessViolation.
    """

    def __init__(
        self,
        world: World,  # World instance (avoid circular import)
        descriptor: SystemDescriptor,
        buffer: SystemResult,
    ):
        self._world = world
        self._descriptor = descriptor
        self._buffer = buffer
        self._sync_runner: SyncRunner = SyncRunner.get()

    def _check_readable(self, *types: type | Any) -> None:
        if self._descriptor.is_dev_mode():
            return
        for t in types:
            component_type = get_type(t) if not isinstance(t, type) else t
            if not self._descriptor.can_read_type(component_type):
                raise AccessViolationError(
                    f"System '{self._descriptor.name}' cannot read {component_type.__name__}: "
                    f"not in readable types"
                )

    def _check_writable(self, component: type | Any) -> None:
        from ..core.system import SystemMode

        if self._descriptor.is_dev_mode():
            return

        component_type: type = get_type(component) if not isinstance(component, type) else component

        # READONLY mode cannot write at all
        if self._descriptor.mode == SystemMode.READONLY:
            raise AccessViolationError(
                f"System '{self._descriptor.name}' is READONLY"
                f" and cannot write {component_type.__name__}"
            )

        if self._descriptor.can_write_type(component_type):
            return
        if self._descriptor.can_read_type(component_type):
            raise AccessViolationError(
                f"System '{self._descriptor.name}' cannot"
                f" write {component_type.__name__}: "
                f"declared as read-only"
            )
        raise AccessViolationError(
            f"System '{self._descriptor.name}': {component_type.__name__}: not in writable types"
        )

    def __getitem__(self, key: tuple[EntityId, type[T]]) -> Copy[T]:
        """Get directly the component T for the entity in key.

        Example: world[entity, Position] -> Position
        """
        entity, component_type = key
        return self.get(entity, component_type)

    def __setitem__(self, key: tuple[EntityId, type], value: Any) -> None:
        """Set directly the component T for entity in key.

        Example: world[entity, Position] = new_pos.
        """
        entity, _ = key
        self.update(entity, value)

    def __delitem__(self, key: tuple[EntityId, type]) -> None:
        """Delete component.

        Example: Del world[entity, Position].
        """
        entity, component_type = key
        self.remove(entity, component_type)

    def __contains__(self, key: tuple[EntityId, type]) -> bool:
        """(entity, Position) in world."""
        entity, component_type = key
        return self.has(entity, component_type)

    def __call__(self, *component_types: type) -> QueryResult:
        """Create a query for component types.

        Example: world(Position, Velocity) -> QueryResult iterable.
        """
        self._check_readable(*component_types)
        return QueryResult(self, component_types)

    def __iter__(self) -> Iterator[EntityId]:
        """Iterate over entities.

        Example: For entity in world: ...
        """
        return self.entities()

    def get(self, entity: EntityId, component_type: type[T]) -> Copy[T]:
        """Get component copy (from buffer or storage).

        ALWAYS returns a copy to prevent accidental mutation of world state.
        Modifications must be written back explicitly via world[entity, Type] = component.
        """
        return cast(T, self._sync_runner.run(self.get_async(entity, component_type)))

    def has(self, entity: EntityId, component_type: type) -> bool:
        """Check if entity has a specific component type."""
        self._check_readable(component_type)

        if entity in self._buffer.inserts and any(
            get_type(c) is component_type for c in self._buffer.inserts[entity]
        ):
            return True
        if entity in self._buffer.removes and component_type in self._buffer.removes[entity]:
            return False

        return self._world._has_component(entity, component_type)

    def _query_raw(
        self,
        *component_types: type,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Internal query returning (entity, (comp1, comp2, ...))."""
        return self._sync_runner.iterate(self._query_raw_async(*component_types))

    def query(
        self,
        *component_types: type,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Query entities with components. Returns (entity, (comp1, comp2, ...))."""
        self._check_readable(*component_types)
        return self._query_raw(*component_types)

    async def _query_raw_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Internal async query returning (entity, (comp1, comp2, ...))."""
        yielded_entities = set()

        async for entity, components in self._world._query_components_async(*component_types):
            should_skip = False
            if entity in self._buffer.destroys:
                continue
            for comp_type in component_types:
                if entity in self._buffer.removes and comp_type in self._buffer.removes[entity]:
                    should_skip = True
                    break
            if should_skip:
                continue

            result = []
            for comp_type, comp in zip(component_types, components, strict=False):
                if entity in self._buffer.updates and comp_type in self._buffer.updates[entity]:
                    result.append(
                        copy.deepcopy(get_component(self._buffer.updates[entity][comp_type]))
                    )
                else:
                    result.append(copy.deepcopy(get_component(comp)))
            yielded_entities.add(entity)
            # Yield either from storage or updated from buffer
            yield entity, tuple(result)

        # At this point we have yielded all entities that has components matching in storage.
        # Now we check inserted or updated components.
        for entity in list(self._buffer.updates.keys()) + list(self._buffer.inserts.keys()):
            if entity in yielded_entities or entity in self._buffer.destroys:
                continue

            has_all = True
            result = []
            for comp_type in component_types:
                comp = None

                if entity in self._buffer.updates and comp_type in self._buffer.updates[entity]:
                    comp = self._buffer.updates[entity][comp_type]
                elif entity in self._buffer.inserts:
                    for inserted_comp in self._buffer.inserts[entity]:
                        if get_type(inserted_comp) is comp_type:
                            comp = inserted_comp
                            break
                if comp is None:
                    comp = await self._world._get_component_async(entity, comp_type)

                if entity in self._buffer.removes and comp_type in self._buffer.removes[entity]:
                    has_all = False
                    break

                if comp is None:
                    has_all = False
                    break

                result.append(copy.deepcopy(get_component(comp)))

            if has_all:
                yielded_entities.add(entity)
                yield entity, tuple(result)

    async def query_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Query entities with components asynchronously. Returns (entity, (comp1, comp2, ...)).

        Async variant for use in async systems. For distributed storage, this enables
        efficient remote queries.

        Args:
            *component_types: Component types to query for.

        Yields:
            Tuples of (entity, (component1, component2, ...)) for each match.
        """
        self._check_readable(*component_types)
        async for entity, components in self._query_raw_async(*component_types):
            yield entity, components

    async def get_async(self, entity: EntityId, component_type: type[T]) -> Copy[T]:
        """Get component asynchronously, checking buffer first (read own writes).

        Async variant for use in async systems. For distributed storage, this enables
        efficient remote component fetches.

        Args:
            entity: Entity to query.
            component_type: Type of component to retrieve.

        Returns:
            Component instance.

        Raises:
            KeyError: If entity does not have the component.
        """
        self._check_readable(component_type)

        if entity in self._buffer.updates and component_type in self._buffer.updates[entity]:
            return cast(
                T, copy.deepcopy(get_component(self._buffer.updates[entity][component_type]))
            )

        if entity in self._buffer.inserts:
            for comp in self._buffer.inserts[entity]:
                if get_type(comp) is component_type:
                    return cast(T, copy.deepcopy(get_component(comp)))

        if component := await self._world._get_component_async(entity, component_type):
            return copy.deepcopy(component)
        elif entity in self._buffer.destroys:
            raise KeyError(f"Entity {entity} has been destroyed")
        else:
            raise KeyError(f"Entity {entity} has no component {component_type.__name__}")

    def singleton(self, component_type: type[T]) -> Copy[T]:
        """Get singleton component from WORLD entity."""
        result = self.get(SystemEntity.WORLD, component_type)
        if result is None:
            raise KeyError(f"No singleton {component_type.__name__} registered")
        return result

    def entities(self) -> Iterator[EntityId]:
        """Iterate all entities."""
        return self._world._all_entities()

    def entity(self, entity_id: EntityId) -> EntityHandle:
        """Get handle for convenient single-entity operations."""
        return EntityHandle(self, entity_id)

    def update(self, entity: EntityId, component: Any) -> None:
        """Update/set component on entity."""
        comp_type = get_type(component)
        self._check_writable(component)

        if entity not in self._buffer.updates:
            self._buffer.updates[entity] = {}
        self._buffer.updates[entity][comp_type] = component

    def update_singleton(self, component: Any) -> None:
        """Update/set singleton component on WORLD entity."""
        comp_type = get_type(component)
        self._check_writable(component)

        if SystemEntity.WORLD not in self._buffer.updates:
            self._buffer.updates[SystemEntity.WORLD] = {}
        self._buffer.updates[SystemEntity.WORLD][comp_type] = component

    def insert(self, entity: EntityId, component: Any) -> None:
        """Add new component to entity."""
        self._check_writable(component)

        if entity not in self._buffer.inserts:
            self._buffer.inserts[entity] = []
        self._buffer.inserts[entity].append(component)

    def remove(self, entity: EntityId, component_type: type) -> None:
        """Remove component from entity."""
        self._check_writable(component_type)

        if entity not in self._buffer.removes:
            self._buffer.removes[entity] = []
        self._buffer.removes[entity].append(component_type)

    def spawn(self, *components: Any) -> EntityId:
        """Spawn new entity with components. Returns provisional ID."""
        seen_types: set[type] = set()
        for comp in components:
            comp_type = get_type(comp)
            self._check_writable(comp)
            if comp_type in seen_types:
                warnings.warn(
                    f"spawn() received multiple components of type {comp_type.__name__}. "
                    f"Only the last one will be kept.",
                    stacklevel=2,
                )
            seen_types.add(comp_type)

        self._buffer.spawns.append(components)
        # Return provisional ID - actual ID assigned at apply time
        return EntityId(shard=0, index=-len(self._buffer.spawns), generation=0)

    def destroy(self, entity: EntityId) -> None:
        """Queue entity for destruction."""
        self._buffer.destroys.append(entity)

    def merge_entities(
        self,
        entities: list[EntityId],
        into: EntityId | None = None,
    ) -> EntityId:
        """Merge multiple entities into one using Mergeable components."""
        # TODO: Implement using merge_components from component.py
        raise NotImplementedError("Entity merging not yet implemented")

    def split_entity(
        self,
        entity: EntityId,
        ratio: float = 0.5,
    ) -> tuple[EntityId, EntityId]:
        """Split entity into two using Splittable components."""
        # TODO: Implement using component protocols
        raise NotImplementedError("Entity splitting not yet implemented")

    def get_copy(self, entity: EntityId, component_type: type[T]) -> Copy[T]:
        """Get component copy. Alias for get() with explicit naming."""
        return self.get(entity, component_type)

    async def get_copy_async(self, entity: EntityId, component_type: type[T]) -> Copy[T]:
        """Get component copy asynchronously. Alias for get_async()."""
        return await self.get_async(entity, component_type)

    def query_copies(
        self,
        *component_types: type,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        """Query entities returning component copies. Alias for query()."""
        return self.query(*component_types)

    async def query_copies_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        """Query entities asynchronously returning copies. Alias for query_async()."""
        async for item in self.query_async(*component_types):
            yield item


# TODO: Implement PureReadAccess (ScopedAccess without write methods)
# TODO: Implement cross-shard access proxy for distributed mode
