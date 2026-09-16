"""World depends on the Storage and ExecutionStrategy protocols, nothing more."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from agentecs.models.identity import EntityId
from agentecs.models.system import SystemDescriptor
from agentecs.protocols.execution import SystemExecutor
from agentecs.services.world.world import World


class StubStorage:
    """Minimal Storage stub: only what World touches during construction and spawn."""

    def __init__(self) -> None:
        self._components: dict[EntityId, dict[type, Any]] = {}
        self._next = 1000

    def create_entity(self) -> EntityId:
        entity = EntityId(shard=0, index=self._next, generation=0)
        self._next += 1
        self._components[entity] = {}
        return entity

    def entity_exists(self, entity: EntityId) -> bool:
        return entity in self._components

    def set_component(self, entity: EntityId, component: Any) -> None:
        self._components.setdefault(entity, {})[type(component)] = component

    def get_component(self, entity: EntityId, component_type: type, copy: bool = True) -> Any:
        return self._components.get(entity, {}).get(component_type)

    def query(self, *component_types: type, copy: bool = True) -> Iterator[Any]:
        return iter(())


class StubExecution:
    """Minimal ExecutionStrategy stub recording the executor it was handed."""

    def __init__(self) -> None:
        self.registered: list[SystemDescriptor] = []
        self.ticked_with: SystemExecutor | None = None

    def register_system(self, descriptor: SystemDescriptor) -> None:
        self.registered.append(descriptor)

    async def tick_async(self, world: SystemExecutor) -> None:
        self.ticked_with = world


@pytest.mark.asyncio
async def test_world_runs_on_stub_seams():
    """World needs only the two protocols, and hands itself to the strategy."""
    storage = StubStorage()
    execution = StubExecution()

    world = World(storage, execution)
    entity = world.spawn()
    assert storage.entity_exists(entity)

    await world.tick_async()
    assert execution.ticked_with is world
    assert isinstance(world, SystemExecutor)


def test_world_construction_touches_no_storage_internals():
    """World builds against a storage that has no _components attribute at all.

    Why: construction used to seed reserved entities by writing into the storage's
    private _components dict. The allocator registers them now, so a conforming
    Storage owes World nothing beyond the protocol.
    """

    class ProtocolOnlyStorage:
        """Storage stub whose backing store is deliberately named something else."""

        def __init__(self) -> None:
            self._store: dict[EntityId, dict[type, Any]] = {}
            self._next = 1000

        def create_entity(self) -> EntityId:
            entity = EntityId(shard=0, index=self._next, generation=0)
            self._next += 1
            self._store[entity] = {}
            return entity

        def entity_exists(self, entity: EntityId) -> bool:
            return entity in self._store

        def set_component(self, entity: EntityId, component: Any) -> None:
            self._store.setdefault(entity, {})[type(component)] = component

        def get_component(self, entity: EntityId, component_type: type, copy: bool = True) -> Any:
            return self._store.get(entity, {}).get(component_type)

        def query(self, *component_types: type, copy: bool = True) -> Iterator[Any]:
            return iter(())

    storage = ProtocolOnlyStorage()

    world = World(storage, StubExecution())

    assert not hasattr(storage, "_components")
    assert world.spawn() is not None
