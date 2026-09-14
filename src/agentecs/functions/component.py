"""Utility functions for combining and splitting components.

These are stateless functions that apply protocol behavior when available
and otherwise use framework fallbacks.
"""

from __future__ import annotations

import copy
import hashlib
from typing import cast

from agentecs.models.component import Combinable, Splittable


def combine_protocol_or_fallback[T](comp1: T, comp2: T) -> T:
    """Combine two components, using Combinable protocol with LWW fallback.

    If comp1 implements Combinable and comp2 is the same type, delegates
    to comp1.__combine__(comp2). Otherwise returns comp2 (last-writer-wins).

    Args:
        comp1: Existing component value.
        comp2: Incoming component value.

    Returns:
        Combined result or comp2 as fallback.
    """
    if not isinstance(comp1, Combinable) or not isinstance(comp2, type(comp1)):
        return comp2
    else:
        return comp1.__combine__(comp2)


def split_protocol_or_fallback[T](comp: T) -> tuple[T, T]:
    """Split a component, using Splittable protocol with deepcopy fallback.

    If comp implements Splittable, delegates to comp.__split__().
    Otherwise returns two independent deep copies.

    Args:
        comp: Component to split.

    Returns:
        Tuple of two components.
    """
    if not isinstance(comp, Splittable):
        return (copy.deepcopy(comp), copy.deepcopy(comp))
    return cast(tuple[T, T], comp.__split__())


def reduce_components[T](items: list[T]) -> T:
    """Reduce a list of components into one.

    Uses sequential combines:
        if __combine__ is defined, merges items using that pairwise;
        otherwise, takes the last item as the result.

    Args:
        items: List of components to reduce (must be same type).

    Returns:
        Single component resulting from reduction.

    Raises:
        ValueError: If items list is empty.
    """
    if not items:
        raise ValueError("Cannot reduce empty list")
    if len(items) == 1:
        return items[0]
    result = items[0]
    for item in items[1:]:
        result = combine_protocol_or_fallback(result, item)
    return result


def stable_component_type_id(cls: type) -> int:
    """Generate deterministic ID from fully qualified class name.

    Uses SHA256 hash of the fully qualified name to ensure same IDs across
    different processes and nodes running the same code.

    Args:
        cls: Component class to generate ID for.

    Returns:
        Deterministic integer ID derived from class name hash.
    """
    fqn = f"{cls.__module__}.{cls.__qualname__}"
    return int(hashlib.sha256(fqn.encode()).hexdigest()[:16], 16)


def is_pydantic(cls: type) -> bool:
    """Check if class is a Pydantic model without importing pydantic.

    Args:
        cls: Class to check.

    Returns:
        True if class inherits from pydantic.BaseModel, False otherwise.
    """
    for base in cls.__mro__:
        if base.__module__.startswith("pydantic") and base.__name__ == "BaseModel":
            return True
    return False
