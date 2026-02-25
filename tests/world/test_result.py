"""Tests for SystemResult op sequencing and compatibility views."""

from dataclasses import dataclass
from typing import Any

import pytest

from agentecs import EntityId, component
from agentecs.world import OpKind, SystemResult, normalize_result


@component
@dataclass(slots=True)
class Count:
    value: int


@component
@dataclass(slots=True)
class Label:
    text: str


def _entity(index: int) -> EntityId:
    return EntityId(shard=0, index=index, generation=0)


def test_ops_preserve_record_order() -> None:
    result = SystemResult()
    entity = _entity(1)

    result.record_update(entity, Count(1))
    result.record_insert(entity, Label("new"))
    result.record_remove(entity, Label)
    result.record_spawn(Count(9))
    result.record_destroy(entity)

    assert [op.kind for op in result.ops] == [
        OpKind.UPDATE,
        OpKind.INSERT,
        OpKind.REMOVE,
        OpKind.SPAWN,
        OpKind.DESTROY,
    ]
    assert [op.op_seq for op in result.ops] == [0, 1, 2, 3, 4]


def test_updates_view_last_write_wins_per_component_type() -> None:
    result = SystemResult()
    entity = _entity(2)

    result.record_update(entity, Count(1))
    result.record_update(entity, Count(2))

    assert result.updates[entity][Count].value == 2
    assert len(result.ops) == 2


def test_merge_preserves_relative_operation_order() -> None:
    left = SystemResult()
    right = SystemResult()
    entity = _entity(3)

    left.record_update(entity, Count(1))
    left.record_insert(entity, Label("left"))

    right.record_remove(entity, Label)
    right.record_destroy(entity)

    left.merge(right)

    assert [op.kind for op in left.ops] == [
        OpKind.UPDATE,
        OpKind.INSERT,
        OpKind.REMOVE,
        OpKind.DESTROY,
    ]
    assert [op.op_seq for op in left.ops] == [0, 1, 2, 3]


def test_record_update_rejects_none_entity() -> None:
    result = SystemResult()

    with pytest.raises(ValueError, match="record_update"):
        result.record_update(None, Count(1))  # type: ignore[arg-type]


def test_is_empty_tracks_queued_operations() -> None:
    result = SystemResult()

    assert result.is_empty()

    result.record_spawn()

    assert not result.is_empty()


def test_normalize_result_dict_requires_entity_id_keys() -> None:
    raw: Any = {"not-an-entity": Count(1)}

    with pytest.raises(TypeError, match="Expected EntityId key"):
        normalize_result(raw)


def test_normalize_result_list_requires_entity_id_entries() -> None:
    raw: Any = [("not-an-entity", Count(1))]

    with pytest.raises(TypeError, match="Expected EntityId"):
        normalize_result(raw)
