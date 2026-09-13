"""System execution results.

Usage:
    # Systems can record updates explicitly:
    result = SystemResult()
    result.record_update(entity, new_pos)
    return result

    # Systems can also return shorthand formats:
    return {entity: {Position: new_pos}}  # Dict shorthand
    return [(entity, new_pos)]  # List shorthand
    return None  # No changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentecs.models.component import get_type
from agentecs.models.identity import EntityId


class OpKind(StrEnum):
    """Operations available to perform."""

    UPDATE = "update"
    INSERT = "insert"
    REMOVE = "remove"
    SPAWN = "spawn"
    DESTROY = "destroy"


@dataclass(frozen=True, slots=True)
class MutationOp:
    """Dataclass to store one mutation operation."""

    op_seq: int
    kind: OpKind
    entity: EntityId | None = None
    component: Any | None = None
    component_type: type | None = None
    spawn_components: tuple[Any, ...] | None = None


@dataclass(slots=True)
class SystemResult:
    """Accumulated changes from system execution."""

    _ops: list[MutationOp] = field(default_factory=list)
    _next_op_seq: int = 0
    _update_indices: list[int] = field(default_factory=list)
    _insert_indices: list[int] = field(default_factory=list)
    _remove_indices: list[int] = field(default_factory=list)
    _spawn_indices: list[int] = field(default_factory=list)
    _destroy_indices: list[int] = field(default_factory=list)

    def record_update(self, entity: EntityId, component: Any) -> None:
        """Record an update operation for an entity's component."""
        if entity is None:
            raise ValueError("record_update requires a non-None entity")
        if component is None:
            raise ValueError("record_update requires a non-None component")

        op = MutationOp(
            op_seq=self._next_op_seq,
            kind=OpKind.UPDATE,
            entity=entity,
            component=component,
            component_type=get_type(component),
        )
        self._ops.append(op)
        self._update_indices.append(self._next_op_seq)
        self._next_op_seq += 1

    def record_insert(self, entity: EntityId, component: Any) -> None:
        """Record an insert operation for an entity's component."""
        if entity is None:
            raise ValueError("record_insert requires a non-None entity")
        if component is None:
            raise ValueError("record_insert requires a non-None component")

        op = MutationOp(
            op_seq=self._next_op_seq,
            kind=OpKind.INSERT,
            entity=entity,
            component=component,
            component_type=get_type(component),
        )
        self._ops.append(op)
        self._insert_indices.append(self._next_op_seq)
        self._next_op_seq += 1

    def record_remove(self, entity: EntityId, component_type: type) -> None:
        """Record a remove operation for an entity's component type."""
        if entity is None:
            raise ValueError("record_remove requires a non-None entity")
        if component_type is None:
            raise ValueError("record_remove requires a non-None component_type")

        op = MutationOp(
            op_seq=self._next_op_seq,
            kind=OpKind.REMOVE,
            entity=entity,
            component_type=component_type,
        )
        self._ops.append(op)
        self._remove_indices.append(self._next_op_seq)
        self._next_op_seq += 1

    def record_spawn(self, entity: EntityId, components: tuple[Any, ...] | None = None) -> None:
        """Record a spawn operation for a new entity with given components."""
        op = MutationOp(
            op_seq=self._next_op_seq,
            entity=entity,
            kind=OpKind.SPAWN,
            spawn_components=components,
        )
        self._ops.append(op)
        self._spawn_indices.append(self._next_op_seq)
        self._next_op_seq += 1

    def record_destroy(self, entity: EntityId) -> None:
        """Record a destroy operation for an entity."""
        if entity is None:
            raise ValueError("record_destroy requires a non-None entity")

        op = MutationOp(
            op_seq=self._next_op_seq,
            kind=OpKind.DESTROY,
            entity=entity,
        )
        self._ops.append(op)
        self._destroy_indices.append(self._next_op_seq)
        self._next_op_seq += 1

    @property
    def ops(self) -> tuple[MutationOp, ...]:
        """Returns all ops."""
        return tuple(self._ops)

    @property
    def updates(self) -> dict[EntityId, dict[type, Any]]:
        """Returns all updates as {entity: {Type: component}}."""
        result: dict[EntityId, dict[type, Any]] = {}
        for i in self._update_indices:
            op = self._ops[i]
            if op.entity is not None and op.component is not None:
                if op.entity not in result:
                    result[op.entity] = {}
                result[op.entity][get_type(op.component)] = op.component
        return result

    @property
    def inserts(self) -> dict[EntityId, list[Any]]:
        """Returns all inserts as {entity: [components]}."""
        result: dict[EntityId, list[Any]] = {}
        for i in self._insert_indices:
            op = self._ops[i]
            if op.entity is not None and op.component is not None:
                if op.entity not in result:
                    result[op.entity] = []
                result[op.entity].append(op.component)
        return result

    @property
    def removes(self) -> dict[EntityId, list[type]]:
        """Returns all removes as {entity: [component types]}."""
        result: dict[EntityId, list[type]] = {}
        for i in self._remove_indices:
            op = self._ops[i]
            if op.entity is not None and op.component_type is not None:
                if op.entity not in result:
                    result[op.entity] = []
                result[op.entity].append(op.component_type)
        return result

    @property
    def spawns(self) -> list[EntityId]:
        """Returns all spawns as list of entity IDs."""
        return [
            spawn_id for i in self._spawn_indices if (spawn_id := self._ops[i].entity) is not None
        ]

    @property
    def spawn_count(self) -> int:
        """Returns total number of queued spawn operations."""
        return len(self._spawn_indices)

    @property
    def destroys(self) -> list[EntityId]:
        """Returns all destroys as list of entity IDs."""
        return [
            entity for i in self._destroy_indices if (entity := self._ops[i].entity) is not None
        ]

    def is_empty(self) -> bool:
        """Check if this result contains no changes.

        Returns:
            True if result has no updates, inserts, removes, spawns, or destroys.
        """
        return not self._ops

    def merge(self, other: SystemResult) -> None:
        """Merge other result into this one.

        ADDS all ops from other into this result.
        Does NOT check for conflicts or merge individual ops
        caller is responsible for ensuring this is safe.

        Args:
            other: SystemResult to merge into this one.
        """
        for op in other._ops:
            if op.kind == OpKind.UPDATE:
                if op.entity is not None and op.component is not None:
                    self.record_update(op.entity, op.component)
            elif op.kind == OpKind.INSERT:
                if op.entity is not None and op.component is not None:
                    self.record_insert(op.entity, op.component)
            elif op.kind == OpKind.REMOVE:
                if op.entity is not None and op.component_type is not None:
                    self.record_remove(op.entity, op.component_type)
            elif op.kind == OpKind.SPAWN:
                if op.entity is not None and op.spawn_components is not None:
                    self.record_spawn(entity=op.entity, components=op.spawn_components)
            elif op.kind == OpKind.DESTROY:
                if op.entity is not None:
                    self.record_destroy(op.entity)
            else:
                raise ValueError(f"Unknown op kind: {op.kind}")


SystemReturn = (
    None
    | SystemResult
    | dict[EntityId, dict[type, Any]]  # {entity: {Type: component}}
    | dict[EntityId, Any]  # {entity: component} (single type)
    | list[tuple[EntityId, Any]]  # [(entity, component), ...]
)
