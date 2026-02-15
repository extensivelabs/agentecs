"""World: Central coordinator for entities, components, and systems.

Usage:
    world = World()

    # Spawn entities
    entity = world.spawn(Position(0, 0), Velocity(1, 0))

    # Register and run systems
    world.register_system(movement_system)
    await world.tick_async()  # or world.tick() for sync wrapper

    # Merge entities (for agent merging)
    merged = world.merge_entities(agent1, agent2)

    # Split entity (for agent splitting)
    left, right = world.split_entity(agent, ratio=0.5)
"""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any, TypeVar

from agentecs.core.component.models import (
    Mergeable,
    NonMergeableHandling,
    NonSplittableHandling,
    Splittable,
)
from agentecs.core.component.wrapper import get_type
from agentecs.core.identity import EntityId, SystemEntity
from agentecs.core.system import SystemDescriptor
from agentecs.core.types import Copy
from agentecs.storage.local import LocalStorage
from agentecs.storage.protocol import Storage
from agentecs.world.access import ScopedAccess
from agentecs.world.result import SystemResult, normalize_result, validate_result_access

if TYPE_CHECKING:
    from agentecs.core.system import ExecutionStrategy

ComponentT = TypeVar("ComponentT")


class World:
    """Central world state and system execution coordinator.

    Owns storage backend and execution strategy. Systems interact via
    ScopedAccess, not World directly. Execution strategy handles all
    system registration and orchestration.
    """

    def __init__(
        self,
        storage: Storage | None = None,
        execution: ExecutionStrategy | None = None,
    ):
        self._storage = storage or LocalStorage()
        # Import here to avoid circular dependency at module level
        if execution is None:
            from agentecs.scheduling import SimpleScheduler

            execution = SimpleScheduler()
        self._execution = execution
        self._ensure_system_entities()

    def _ensure_system_entities(self) -> None:
        """Create reserved singleton entities if not present."""
        for entity in [SystemEntity.WORLD, SystemEntity.CLOCK]:
            if not self._storage.entity_exists(entity):
                # Bypass allocator
                self._storage._components[entity] = {}  # type: ignore

    def spawn(self, *components: Any) -> EntityId:
        """Create entity with components. For use outside systems."""
        entity = self._storage.create_entity()
        seen_types: set[type] = set()
        for comp in components:
            comp_type = get_type(comp)
            if comp_type in seen_types:
                warnings.warn(
                    f"spawn() received multiple components of type {comp_type.__name__}. "
                    f"Only the last one will be kept.",
                    stacklevel=2,
                )
            seen_types.add(comp_type)
            self._storage.set_component(entity, comp)
        return entity

    def destroy(self, entity: EntityId) -> None:
        """Destroy entity. For use outside systems."""
        self._storage.destroy_entity(entity)

    def get_copy(
        self, entity: EntityId, component_type: type[ComponentT]
    ) -> Copy[ComponentT] | None:
        """Get component copy. For use outside systems.

        Returns a deep copy to prevent accidental mutation of world state.
        Modifications must be written back via world.set() or world[entity, Type] = component.
        """
        component = self._storage.get_component(entity, component_type, copy=True)
        return component

    def set(self, entity: EntityId, component: Any) -> None:
        """Set component. For use outside systems."""
        self._storage.set_component(entity, component)

    def singleton_copy(self, component_type: type[ComponentT]) -> Copy[ComponentT] | None:
        """Get singleton component from WORLD entity."""
        return self.get_copy(SystemEntity.WORLD, component_type)

    def set_singleton(self, component: Any) -> None:
        """Set singleton component on WORLD entity."""
        self.set(SystemEntity.WORLD, component)

    def query_copies(self, *component_types: type) -> Iterator[tuple[EntityId, ...]]:
        """Query entities with specified component types. For use outside systems.

        Returns iterator of tuples: (entity, component1, component2, ...)
        where components are deep copies.

        Example:
            >>> for entity, pos, vel in world.query(Position, Velocity):
            ...     # Process entities with both Position and Velocity
            ...     pass
        """
        for entity, components in self._storage.query(*component_types, copy=True):
            yield (entity, *components)

    def merge_entities(
        self,
        entity1: EntityId,
        entity2: EntityId,
        on_non_mergeable: NonMergeableHandling = NonMergeableHandling.FIRST,
    ) -> EntityId:
        """Merge two entities into a single new entity.

        Components implementing Mergeable protocol are merged via __merge__.
        Non-mergeable components are handled according to the strategy.

        Args:
            entity1: First entity to merge.
            entity2: Second entity to merge.
            on_non_mergeable: How to handle non-mergeable components.
                - ERROR: Raise TypeError if any component not Mergeable
                - FIRST: Keep component from entity1
                - SECOND: Keep component from entity2
                - SKIP: Don't include in merged entity

        Returns:
            EntityId of the newly created merged entity.

        Raises:
            ValueError: If either entity doesn't exist.
            TypeError: If on_non_mergeable=ERROR and component not Mergeable.

        Example:
            >>> merged = world.merge_entities(agent1, agent2)
            >>> # agent1 and agent2 are destroyed
            >>> # merged has combined components
        """
        if not self._storage.entity_exists(entity1):
            raise ValueError(f"Entity {entity1} does not exist")
        if not self._storage.entity_exists(entity2):
            raise ValueError(f"Entity {entity2} does not exist")

        # Collect all component types from both entities
        types1 = self._storage.get_component_types(entity1)
        types2 = self._storage.get_component_types(entity2)
        all_types = types1 | types2

        # Merge components using strategy functions
        merged_components: list[Any] = []
        non_mergeable_strategy = on_non_mergeable.get_strategy()

        for comp_type in all_types:
            comp1 = self._storage.get_component(entity1, comp_type)
            comp2 = self._storage.get_component(entity2, comp_type)

            if comp1 is not None and comp2 is not None:
                # Both have this component - merge using protocol or strategy
                if isinstance(comp1, Mergeable):
                    from agentecs.core.component.operations import merge_using_protocol

                    merged = merge_using_protocol(comp1, comp2)
                else:
                    merged = non_mergeable_strategy(comp1, comp2)

                if merged is not None:
                    merged_components.append(merged)

            elif comp1 is not None:
                # Only entity1 has this component
                merged_components.append(comp1)
            elif comp2 is not None:
                # Only entity2 has this component
                merged_components.append(comp2)

        # Create merged entity and destroy originals
        merged_entity = self.spawn(*merged_components)
        self.destroy(entity1)
        self.destroy(entity2)

        return merged_entity

    def split_entity(
        self,
        entity: EntityId,
        ratio: float = 0.5,
        on_non_splittable: NonSplittableHandling = NonSplittableHandling.BOTH,
    ) -> tuple[EntityId, EntityId]:
        """Split one entity into two new entities.

        Components implementing Splittable protocol are split via __split__.
        Non-splittable components are handled according to the strategy.

        Args:
            entity: Entity to split.
            ratio: Split ratio for Splittable components (0.0 to 1.0).
                   0.5 means equal split.
            on_non_splittable: How to handle non-splittable components.
                - ERROR: Raise TypeError if any component not Splittable
                - FIRST: Give component to first entity only
                - BOTH: Clone component to both entities (default)
                - SKIP: Don't include in either entity

        Returns:
            Tuple of (first_entity, second_entity) IDs.

        Raises:
            ValueError: If entity doesn't exist or ratio out of range.
            TypeError: If on_non_splittable=ERROR and component not Splittable.

        Example:
            >>> left, right = world.split_entity(agent, ratio=0.5)
            >>> # original agent is destroyed
            >>> # left and right have split components
        """
        if not self._storage.entity_exists(entity):
            raise ValueError(f"Entity {entity} does not exist")
        if not 0.0 <= ratio <= 1.0:
            raise ValueError(f"Ratio must be between 0.0 and 1.0, got {ratio}")

        # Collect all components and split using strategy functions
        comp_types = self._storage.get_component_types(entity)
        non_splittable_strategy = on_non_splittable.get_strategy()

        first_components: list[Any] = []
        second_components: list[Any] = []

        for comp_type in comp_types:
            comp = self._storage.get_component(entity, comp_type)
            if comp is None:
                continue

            # Split using protocol or strategy
            if isinstance(comp, Splittable):
                from agentecs.core.component.operations import split_using_protocol

                left, right = split_using_protocol(comp, ratio)
            else:
                left, right = non_splittable_strategy(comp, ratio)

            if left is not None:
                first_components.append(left)
            if right is not None:
                second_components.append(right)

        # Create new entities and destroy original
        first_entity = self.spawn(*first_components)
        second_entity = self.spawn(*second_components)
        self.destroy(entity)

        return first_entity, second_entity

    def _get_component(
        self, entity: EntityId, component_type: type[ComponentT]
    ) -> ComponentT | None:
        return self._storage.get_component(entity, component_type)

    def _has_component(self, entity: EntityId, component_type: type) -> bool:
        return self._storage.has_component(entity, component_type)

    def _query_components(
        self,
        *component_types: type,
    ) -> Iterator[tuple[EntityId, tuple[Any, ...]]]:
        return self._storage.query(*component_types)

    def _all_entities(self) -> Iterator[EntityId]:
        return self._storage.all_entities()

    def _get_component_types(self, entity: EntityId) -> frozenset[type]:
        return self._storage.get_component_types(entity)

    # Async variants for internal use (enables async ScopedAccess methods)

    async def _get_component_async(
        self, entity: EntityId, component_type: type[ComponentT]
    ) -> ComponentT | None:
        return await self._storage.get_component_async(entity, component_type)

    async def _query_components_async(
        self,
        *component_types: type,
    ) -> AsyncIterator[tuple[EntityId, tuple[Any, ...]]]:
        async for x in self._storage.query_async(*component_types):
            yield x

    def register_system(self, descriptor: SystemDescriptor) -> None:
        """Register system for execution.

        Delegates to the injected execution strategy.
        """
        self._execution.register_system(descriptor)

    def register_systems(self, *descriptors: SystemDescriptor) -> None:
        """Register multiple systems."""
        for d in descriptors:
            self.register_system(d)

    async def execute_system_async(self, descriptor: SystemDescriptor) -> SystemResult:
        """Execute single system asynchronously, returning collected changes.

        Handles both sync and async systems automatically based on descriptor.is_async.
        """
        result_buffer = SystemResult()
        access = ScopedAccess(world=self, descriptor=descriptor, buffer=result_buffer)

        # Run system (async if needed)
        if descriptor.is_async:
            returned = await descriptor.run(access)
        else:
            returned = descriptor.run(access)

        # Merge return value into buffer
        if returned is not None:
            normalized = normalize_result(returned)
            result_buffer.merge(normalized)

        validate_result_access(
            result_buffer,
            descriptor.writable_types(),
            descriptor.name,
        )

        return result_buffer

    def execute_system(self, descriptor: SystemDescriptor) -> SystemResult:
        """Execute single system synchronously (wrapper for execute_system_async).

        For backward compatibility. Prefer execute_system_async() in async contexts.
        """
        return asyncio.run(self.execute_system_async(descriptor))

    async def apply_result_async(self, result: SystemResult) -> list[EntityId]:
        """Apply system result to world state asynchronously.

        For distributed storage, this enables parallel updates across shards.
        For local storage, this is a simple async wrapper.

        Args:
            result: System execution result containing all changes.

        Returns:
            List of newly created entity IDs from spawns.
        """
        # Handle spawns first to get real entity IDs
        new_entities: list[EntityId] = []
        for components in result.spawns:
            entity = self._storage.create_entity()
            new_entities.append(entity)
            for comp in components:
                self._storage.set_component(entity, comp)

        # Apply updates asynchronously
        await self._storage.apply_updates_async(
            updates=result.updates,
            inserts=result.inserts,
            removes=result.removes,
            destroys=result.destroys,
        )

        return new_entities

    def apply_result(self, result: SystemResult) -> list[EntityId]:
        """Apply system result to world state (sync wrapper for backward compatibility).

        Prefer apply_result_async() in async contexts.

        Args:
            result: System execution result containing all changes.

        Returns:
            List of newly created entity IDs from spawns.
        """
        return asyncio.run(self.apply_result_async(result))

    async def tick_async(self) -> None:
        """Execute all registered systems once asynchronously.

        Delegates to the injected execution strategy, which handles
        parallelization, conflict detection, or other orchestration logic.
        """
        await self._execution.tick_async(self)

    def tick(self) -> None:
        """Execute all registered systems once synchronously (wrapper for tick_async).

        For backward compatibility and simple scripts. Prefer tick_async() in async contexts.
        """
        asyncio.run(self.tick_async())

    def snapshot(self) -> bytes:
        """Serialize world state."""
        return self._storage.snapshot()

    def restore(self, data: bytes) -> None:
        """Restore from snapshot."""
        self._storage.restore(data)
