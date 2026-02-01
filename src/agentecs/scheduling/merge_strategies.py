"""Pure functions for merge strategies.

Stateless functions implementing different strategies for resolving
write conflicts when multiple systems update the same (entity, component).
"""

from __future__ import annotations

from typing import Any

from agentecs.core.component.models import Mergeable
from agentecs.core.identity import EntityId
from agentecs.world.result import ConflictError, SystemResult


def merge_last_writer_wins(
    results: list[SystemResult],
    system_names: list[str],
) -> SystemResult:
    """Merge results where later systems overwrite earlier ones.

    Systems are processed in order (registration order). If multiple systems
    write the same (entity, component), the last one wins.

    Args:
        results: List of SystemResult in registration order.
        system_names: System names for error messages (parallel to results).

    Returns:
        Merged SystemResult.
    """
    merged = SystemResult()

    for result in results:
        # Updates: later overwrites earlier (dict.update semantics)
        for entity, components in result.updates.items():
            if entity not in merged.updates:
                merged.updates[entity] = {}
            merged.updates[entity].update(components)

        # Inserts: accumulate all
        for entity, component_list in result.inserts.items():
            if entity not in merged.inserts:
                merged.inserts[entity] = []
            merged.inserts[entity].extend(component_list)

        # Removes: accumulate all
        for entity, types in result.removes.items():
            if entity not in merged.removes:
                merged.removes[entity] = []
            merged.removes[entity].extend(types)

        # Spawns and destroys: accumulate
        merged.spawns.extend(result.spawns)
        merged.destroys.extend(result.destroys)

    return merged


def merge_mergeable_first(
    results: list[SystemResult],
    system_names: list[str],
) -> SystemResult:
    """Merge results using Mergeable protocol when available.

    For each (entity, component) written by multiple systems:
    - If component implements Mergeable, use __merge__ to combine
    - Otherwise, fall back to last-writer-wins

    Args:
        results: List of SystemResult in registration order.
        system_names: System names for error messages.

    Returns:
        Merged SystemResult.
    """
    merged = SystemResult()

    # Track all writes per (entity, type) to detect conflicts
    writes: dict[tuple[EntityId, type], list[tuple[int, Any]]] = {}

    for i, result in enumerate(results):
        for entity, components in result.updates.items():
            for comp_type, comp in components.items():
                key = (entity, comp_type)
                if key not in writes:
                    writes[key] = []
                writes[key].append((i, comp))

    # Resolve each (entity, type)
    for (entity, comp_type), write_list in writes.items():
        if len(write_list) == 1:
            # No conflict
            _, comp = write_list[0]
            if entity not in merged.updates:
                merged.updates[entity] = {}
            merged.updates[entity][comp_type] = comp
        else:
            # Multiple writes - try Mergeable, else last wins
            _, first_comp = write_list[0]
            result_comp = first_comp

            for _, next_comp in write_list[1:]:
                if isinstance(result_comp, Mergeable):
                    result_comp = result_comp.__merge__(next_comp)
                else:
                    # Fall back to overwrite
                    result_comp = next_comp

            if entity not in merged.updates:
                merged.updates[entity] = {}
            merged.updates[entity][comp_type] = result_comp

    # Handle inserts, removes, spawns, destroys (same as last_writer_wins)
    for result in results:
        for entity, component_list in result.inserts.items():
            if entity not in merged.inserts:
                merged.inserts[entity] = []
            merged.inserts[entity].extend(component_list)

        for entity, types in result.removes.items():
            if entity not in merged.removes:
                merged.removes[entity] = []
            merged.removes[entity].extend(types)

        merged.spawns.extend(result.spawns)
        merged.destroys.extend(result.destroys)

    return merged


def merge_error_on_conflict(
    results: list[SystemResult],
    system_names: list[str],
) -> SystemResult:
    """Merge results, raising error if any conflicts detected.

    Useful for debugging to catch unintended concurrent writes.

    Args:
        results: List of SystemResult in registration order.
        system_names: System names for error messages.

    Returns:
        Merged SystemResult.

    Raises:
        ConflictError: If multiple systems write same (entity, component).
    """
    merged = SystemResult()
    seen_writes: dict[tuple[EntityId, type], str] = {}

    for i, result in enumerate(results):
        system_name = system_names[i] if i < len(system_names) else f"system_{i}"

        for entity, components in result.updates.items():
            for comp_type in components:
                key = (entity, comp_type)
                if key in seen_writes:
                    raise ConflictError(
                        f"Conflict: {system_name} and {seen_writes[key]} both wrote "
                        f"{comp_type.__name__} on entity {entity}"
                    )
                seen_writes[key] = system_name

        merged.merge(result)

    return merged
