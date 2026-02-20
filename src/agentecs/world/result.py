"""System execution results and normalization.

Usage:
    # Systems can return various formats:
    return SystemResult(updates={...})  # Explicit
    return {entity: {Position: new_pos}}  # Dict shorthand
    return [(entity, new_pos)]  # List shorthand
    return None  # No changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agentecs.core.component.wrapper import get_type
from agentecs.core.identity import EntityId

if TYPE_CHECKING:
    pass
else:
    # Import at runtime to avoid circular dependency
    def __getattr__(name: str) -> Any:
        if name == "AccessViolationError":
            from agentecs.world.access import AccessViolationError

            return AccessViolationError
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass
class SystemResult:
    """Accumulated changes from system execution."""

    updates: dict[EntityId, dict[type, Any]] = field(default_factory=dict)
    inserts: dict[EntityId, list[Any]] = field(default_factory=dict)
    removes: dict[EntityId, list[type]] = field(default_factory=dict)
    spawns: list[tuple[Any, ...]] = field(default_factory=list)
    destroys: list[EntityId] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if this result contains no changes.

        Returns:
            True if result has no updates, inserts, removes, spawns, or destroys.
        """
        return (
            not self.updates
            and not self.inserts
            and not self.removes
            and not self.spawns
            and not self.destroys
        )

    def merge(self, other: SystemResult) -> None:
        """Merge other result into this one.

        Combines all changes from other into self, mutating self in place.
        Component updates are merged per-entity, per-type.

        Args:
            other: SystemResult to merge into this one.
        """
        for entity, components in other.updates.items():
            if entity not in self.updates:
                self.updates[entity] = {}
            self.updates[entity].update(components)

        for entity, component_list in other.inserts.items():
            if entity not in self.inserts:
                self.inserts[entity] = []
            self.inserts[entity].extend(component_list)

        for entity, types in other.removes.items():
            if entity not in self.removes:
                self.removes[entity] = []
            self.removes[entity].extend(types)

        self.spawns.extend(other.spawns)
        self.destroys.extend(other.destroys)


SystemReturn = (
    None
    | SystemResult
    | dict[EntityId, dict[type, Any]]  # {entity: {Type: component}}
    | dict[EntityId, Any]  # {entity: component} (single type)
    | list[tuple[EntityId, Any]]  # [(entity, component), ...]
)


def normalize_result(raw: SystemReturn) -> SystemResult:
    """Convert any valid system return format to SystemResult.

    Supports multiple return formats for convenience:
    - None: No changes
    - SystemResult: Direct passthrough
    - Dict[EntityId, Dict[type, Any]]: Entity to component dict
    - Dict[EntityId, Any]: Entity to single component
    - List[Tuple[EntityId, Any]]: List of (entity, component) pairs

    Args:
        raw: System return value in any supported format.

    Returns:
        Normalized SystemResult.

    Raises:
        TypeError: If return value is not a recognized format.
    """
    if raw is None:
        return SystemResult()

    if isinstance(raw, SystemResult):
        return raw

    if isinstance(raw, dict):
        result = SystemResult()
        for entity, value in raw.items():
            if not isinstance(entity, EntityId):
                raise TypeError(f"Expected EntityId key, got {type(entity)}")

            if isinstance(value, dict):
                # {entity: {Type: component}}
                result.updates[entity] = value
            else:
                # {entity: component} - infer type
                result.updates[entity] = {type(value): value}
        return result

    if isinstance(raw, list):
        result = SystemResult()
        for item in raw:
            if not isinstance(item, tuple) or len(item) != 2:
                raise TypeError(f"Expected (EntityId, component) tuple, got {item}")
            entity, component = item
            if not isinstance(entity, EntityId):
                raise TypeError(f"Expected EntityId, got {type(entity)}")

            if entity not in result.updates:
                result.updates[entity] = {}
            result.updates[entity][type(component)] = component
        return result

    raise TypeError(f"Invalid system return type: {type(raw)}")


def validate_result_access(
    result: SystemResult,
    writable: frozenset[type],
    system_name: str,
) -> None:
    """Validate that all written component types are declared.

    Args:
        result: System execution result to validate.
        writable: Set of component types system declared as writable.
        system_name: Name of system for error messages.

    Raises:
        AccessViolationError: If system wrote undeclared component type.
    """
    from agentecs.world.access import AccessViolationError

    if not writable:  # Empty = all (dev mode)
        return

    for _, components in result.updates.items():
        for comp_type in components:
            if comp_type not in writable:
                raise AccessViolationError(
                    f"System '{system_name}' wrote {comp_type.__name__}: not in writable types"
                )

    for _, component_list in result.inserts.items():
        for comp in component_list:
            if get_type(comp) not in writable:
                raise AccessViolationError(
                    f"System '{system_name}' inserted {type(comp).__name__}: not in writable types"
                )


class ConflictError(Exception):
    """Raised when parallel systems write the same component on same entity."""

    pass
