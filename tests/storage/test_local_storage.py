"""Unit tests for LocalStorage shared component behavior."""

from dataclasses import dataclass

import pytest

from agentecs import component
from agentecs.core.component import Shared
from agentecs.core.component.wrapper import WrappedComponent
from agentecs.core.identity.models import EntityId
from agentecs.storage.local import LocalStorage


@component
@dataclass(slots=True)
class Task:
    name: str


@component
@dataclass(slots=True)
class Priority:
    level: int


@pytest.fixture
def shared_pair() -> tuple[LocalStorage, EntityId, EntityId, Task]:
    """Create two entities sharing the same Task instance."""
    storage = LocalStorage()
    entity_a = storage.create_entity()
    entity_b = storage.create_entity()

    shared_task = Task(name="shared")
    storage.set_component(entity_a, Shared(shared_task))
    storage.set_component(entity_b, Shared(shared_task))

    return storage, entity_a, entity_b, shared_task


def test_set_component_with_shared_returns_unwrapped_component() -> None:
    """set_component(Shared(...)) stores and returns the inner component, not the wrapper."""
    storage = LocalStorage()
    entity = storage.create_entity()
    task = Task(name="one")

    storage.set_component(entity, Shared(task))

    value = storage.get_component(entity, Task, copy=False)
    assert value is task
    assert not isinstance(value, WrappedComponent)


def test_same_shared_instance_is_returned_for_two_entities(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """Using one Shared() instance for two entities resolves to one storage object."""
    storage, entity_a, entity_b, shared_task = shared_pair

    task_a = storage.get_component(entity_a, Task, copy=False)
    task_b = storage.get_component(entity_b, Task, copy=False)

    assert task_a is shared_task
    assert task_b is shared_task
    assert task_a is task_b


def test_updates_to_shared_component_propagate_between_entities(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """Mutating a shared component through one entity is visible through other entities."""
    storage, entity_a, entity_b, _ = shared_pair

    task_a = storage.get_component(entity_a, Task, copy=False)
    assert task_a is not None
    task_a.name = "updated"

    task_b = storage.get_component(entity_b, Task, copy=False)
    assert task_b is not None
    assert task_b.name == "updated"


def test_different_shared_wrappers_with_different_objects_do_not_share() -> None:
    """Different wrapped objects must stay isolated even when component values match."""
    storage = LocalStorage()
    entity_a = storage.create_entity()
    entity_b = storage.create_entity()

    first = Task(name="same")
    second = Task(name="same")

    storage.set_component(entity_a, Shared(first))
    storage.set_component(entity_b, Shared(second))

    task_a = storage.get_component(entity_a, Task, copy=False)
    task_b = storage.get_component(entity_b, Task, copy=False)

    assert task_a is first
    assert task_b is second
    assert task_a is not task_b
    assert len(storage._shared_components) == 2


def test_get_component_copy_flag_controls_copy_vs_reference(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """copy=True returns a deep copy while copy=False returns shared reference."""
    storage, entity_a, entity_b, _ = shared_pair

    copy_value = storage.get_component(entity_a, Task, copy=True)
    ref_value = storage.get_component(entity_a, Task, copy=False)

    assert copy_value is not None
    assert ref_value is not None
    assert copy_value is not ref_value

    copy_value.name = "copy-change"
    fresh_a = storage.get_component(entity_a, Task, copy=False)
    assert fresh_a is not None
    assert fresh_a.name == "shared"

    ref_value.name = "ref-change"
    fresh_b = storage.get_component(entity_b, Task, copy=False)
    assert fresh_b is not None
    assert fresh_b.name == "ref-change"


def test_regular_component_set_component_stores_normally() -> None:
    """Non-shared components continue to be stored in regular per-entity storage."""
    storage = LocalStorage()
    entity = storage.create_entity()
    priority = Priority(level=5)

    storage.set_component(entity, priority)

    value = storage.get_component(entity, Priority, copy=False)
    assert value is priority
    assert storage.has_component(entity, Priority)


@pytest.mark.xfail(
    reason=(
        "LocalStorage currently stores non-shared writes by reference, so reusing the same "
        "object across entities aliases state"
    ),
    strict=False,
)
def test_same_non_shared_object_set_on_two_entities_is_isolated() -> None:
    """Captures desired behavior: non-shared writes should not alias across entities."""
    storage = LocalStorage()
    entity_a = storage.create_entity()
    entity_b = storage.create_entity()

    reused = Priority(level=3)
    storage.set_component(entity_a, reused)
    storage.set_component(entity_b, reused)

    value_a = storage.get_component(entity_a, Priority, copy=False)
    value_b = storage.get_component(entity_b, Priority, copy=False)

    assert value_a is not None
    assert value_b is not None
    assert value_a is not value_b

    value_a.level = 99
    assert value_b.level == 3


def test_has_component_returns_true_for_shared_components(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """has_component() treats shared refs as present components."""
    storage, entity_a, _, _ = shared_pair

    assert storage.has_component(entity_a, Task)
    assert not storage.has_component(entity_a, Priority)


def test_get_component_types_includes_shared_component_types(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """get_component_types() includes both regular and shared-backed component types."""
    storage, entity_a, _, _ = shared_pair
    storage.set_component(entity_a, Priority(level=1))

    types = storage.get_component_types(entity_a)

    assert Task in types
    assert Priority in types


def test_query_returns_shared_components_without_mutating_storage_state(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """query() should return shared matches without corrupting internal shared mappings."""
    storage, entity_a, entity_b, shared_task = shared_pair

    refs_before = dict(storage._shared_refs)
    component_ids_before = {k: id(v) for k, v in storage._shared_components.items()}

    ref_rows = list(storage.query(Task, copy=False))
    copy_rows = list(storage.query(Task, copy=True))

    assert {entity for entity, _ in ref_rows} == {entity_a, entity_b}
    assert all(components[0] is shared_task for _, components in ref_rows)
    assert len(copy_rows) == 2
    assert all(components[0] is not shared_task for _, components in copy_rows)

    assert storage._shared_refs == refs_before
    assert {k: id(v) for k, v in storage._shared_components.items()} == component_ids_before


def test_query_single_finds_shared_components(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """query_single() finds shared-backed components for all matching entities."""
    storage, entity_a, entity_b, shared_task = shared_pair

    rows = list(storage.query_single(Task, copy=False))

    assert {entity for entity, _ in rows} == {entity_a, entity_b}
    assert all(task is shared_task for _, task in rows)


def test_remove_component_clears_shared_ref_and_get_returns_none() -> None:
    """remove_component() removes shared mapping and future reads return None."""
    storage = LocalStorage()
    entity = storage.create_entity()
    task = Task(name="one")

    storage.set_component(entity, Shared(task))
    removed = storage.remove_component(entity, Task)

    assert removed
    assert storage.get_component(entity, Task) is None
    assert (entity, Task) not in storage._shared_refs


def test_remove_component_garbage_collects_shared_component_after_last_ref(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """Shared storage slot is reclaimed only after the final entity reference is removed."""
    storage, entity_a, entity_b, _ = shared_pair

    instance_id = storage._shared_refs[(entity_a, Task)]

    storage.remove_component(entity_a, Task)
    assert instance_id in storage._shared_components

    storage.remove_component(entity_b, Task)
    assert instance_id not in storage._shared_components


def test_destroy_entity_cleans_shared_refs_and_orphans(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """destroy_entity() removes per-entity shared refs and reclaims orphaned shared slots."""
    storage, entity_a, entity_b, _ = shared_pair

    instance_id = storage._shared_refs[(entity_a, Task)]

    storage.destroy_entity(entity_a)
    assert (entity_a, Task) not in storage._shared_refs
    assert instance_id in storage._shared_components

    storage.destroy_entity(entity_b)
    assert (entity_b, Task) not in storage._shared_refs
    assert instance_id not in storage._shared_components


def test_snapshot_restore_preserves_shared_component_state(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """snapshot()/restore() keeps shared linkage and mutation propagation intact."""
    storage, entity_a, entity_b, _ = shared_pair
    storage.set_component(entity_a, Priority(level=7))

    snapshot = storage.snapshot()

    restored = LocalStorage()
    restored.restore(snapshot)

    task_a = restored.get_component(entity_a, Task, copy=False)
    task_b = restored.get_component(entity_b, Task, copy=False)
    priority = restored.get_component(entity_a, Priority, copy=False)

    assert task_a is not None
    assert task_b is not None
    assert task_a is task_b
    assert priority is not None and priority.level == 7

    task_a.name = "after-restore"
    restored_task_b = restored.get_component(entity_b, Task, copy=False)
    assert restored_task_b is not None
    assert restored_task_b.name == "after-restore"


def test_remove_component_from_all_removes_shared_type_everywhere(
    shared_pair: tuple[LocalStorage, EntityId, EntityId, Task],
) -> None:
    """remove_component_from_all() clears shared refs/components for the removed type."""
    storage, entity_a, entity_b, _ = shared_pair

    extra = storage.create_entity()
    storage.set_component(extra, Priority(level=9))

    storage.remove_component_from_all(Task)

    assert storage.get_component(entity_a, Task) is None
    assert storage.get_component(entity_b, Task) is None
    assert not storage.has_component(entity_a, Task)
    assert not storage.has_component(entity_b, Task)
    assert all(component_type is not Task for (_, component_type) in storage._shared_refs)
    assert len(storage._shared_components) == 0

    # Unrelated regular types are unaffected.
    assert storage.get_component(extra, Priority, copy=False) is not None
