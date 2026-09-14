"""Normalization, merging, and access validation of system results."""

from __future__ import annotations

from collections.abc import Iterable

from agentecs.models.component import get_type
from agentecs.models.errors import AccessViolationError
from agentecs.models.identity import EntityId
from agentecs.models.query import AccessPattern, AllAccess, NoAccess, QueryAccess, TypeAccess
from agentecs.models.result import SystemResult, SystemReturn


def merge_results(results: Iterable[SystemResult]) -> SystemResult:
    """Concatenate results in order of operation."""
    merged = SystemResult()
    for result in results:
        merged.merge(result)
    return merged


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
                for _, comp in value.items():
                    result.record_update(entity, comp)
            else:
                result.record_update(entity, value)
        return result

    if isinstance(raw, list):
        result = SystemResult()
        for item in raw:
            if isinstance(item, tuple) and len(item) == 2:
                entity, comp = item
                if not isinstance(entity, EntityId):
                    raise TypeError(f"Expected EntityId, got {type(entity)}")
                result.record_update(entity, comp)
            else:
                raise TypeError(f"Invalid list item format: {item}")
        return result

    raise TypeError(f"Invalid system return type: {type(raw)}")


def validate_result_access(
    result: SystemResult,
    writes: AccessPattern,
    system_name: str,
) -> None:
    """Validate that all written component types are declared.

    Args:
        result: System execution result to validate.
        writes: Declared write access contract for the system.
        system_name: Name of system for error messages.

    Raises:
        AccessViolationError: If system wrote undeclared component type.
    """
    if isinstance(writes, AllAccess):
        return

    writable: frozenset[type] = frozenset()
    if isinstance(writes, NoAccess):
        pass  # empty frozenset rejects all writes
    elif isinstance(writes, TypeAccess):
        writable = writes.types
    elif isinstance(writes, QueryAccess):
        writable = writes.types()
    else:
        raise TypeError(f"Unrecognized AccessPattern: {type(writes)}")

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
                    f"System '{system_name}' inserted {get_type(comp).__name__}:"
                    f" not in writable types"
                )
