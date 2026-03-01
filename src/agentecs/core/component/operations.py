"""Pure functions for merge and split strategies.

These are stateless, SOLID functions that implement different handling strategies
for merging and splitting components during entity operations.
"""

from __future__ import annotations

import copy
from typing import cast

from agentecs.core.component.models import Combinable, Splittable


def combine_protocol_or_fallback[T](comp1: T, comp2: T) -> T:
    """Combine two components using the Mergeable protocol.

    Args:
        comp1: First component (must implement Combinable).
        comp2: Second component updating the first (must be same type as comp1).

    Returns:
        Merged component via __combine__ method or comp2.
    """
    if not isinstance(comp1, Combinable) or not isinstance(comp2, type(comp1)):
        return comp2
    else:
        return comp1.__combine__(comp2)


def split_protocol_or_fallback[T](comp: T) -> tuple[T, T]:
    """Split a component using the Splittable protocol.

    Args:
        comp: Component to split (must implement Splittable).

    Returns:
        Tuple of (first_split, second_split) via __split__ method.

    Raises:
        TypeError: If comp doesn't implement Splittable.
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
