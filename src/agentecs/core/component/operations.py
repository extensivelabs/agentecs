"""Pure functions for merge and split strategies.

These are stateless, SOLID functions that implement different handling strategies
for merging and splitting components during entity operations.
"""

from __future__ import annotations

import copy
from typing import TypeVar, cast

from agentecs.core.component.models import Mergeable, Splittable

T = TypeVar("T")


# Merge strategies


def merge_using_protocol(comp1: T, comp2: T) -> T:
    """Merge two components using the Mergeable protocol.

    Args:
        comp1: First component (must implement Mergeable).
        comp2: Second component.

    Returns:
        Merged component via __merge__ method.

    Raises:
        TypeError: If comp1 doesn't implement Mergeable.
    """
    if not isinstance(comp1, Mergeable):
        raise TypeError(f"{type(comp1).__name__} does not implement Mergeable protocol")
    return comp1.__merge__(comp2)  # type: ignore[return-value]


def merge_take_first(comp1: T, comp2: T) -> T:
    """Take the first component, discard the second.

    Args:
        comp1: First component.
        comp2: Second component (ignored).

    Returns:
        The first component unchanged.
    """
    return comp1


def merge_take_second(comp1: T, comp2: T) -> T:
    """Take the second component, discard the first.

    Args:
        comp1: First component (ignored).
        comp2: Second component.

    Returns:
        The second component unchanged.
    """
    return comp2


def merge_skip(comp1: T, comp2: T) -> None:
    """Skip both components (exclude from merged entity).

    Args:
        comp1: First component (ignored).
        comp2: Second component (ignored).

    Returns:
        None to indicate component should be skipped.
    """
    return None


def merge_error(comp1: T, comp2: T) -> T:
    """Raise an error for non-mergeable components.

    Args:
        comp1: First component.
        comp2: Second component.

    Returns:
        Never returns.

    Raises:
        TypeError: Always raised to indicate incompatible components.
    """
    raise TypeError(f"Component {type(comp1).__name__} is not Mergeable and strategy is ERROR")


# Split strategies


def split_using_protocol(comp: T, ratio: float) -> tuple[T, T]:
    """Split a component using the Splittable protocol.

    Args:
        comp: Component to split (must implement Splittable).
        ratio: Split ratio (0.0 to 1.0).

    Returns:
        Tuple of (first_split, second_split) via __split__ method.

    Raises:
        TypeError: If comp doesn't implement Splittable.
    """
    if not isinstance(comp, Splittable):
        raise TypeError(f"{type(comp).__name__} does not implement Splittable protocol")
    return cast(tuple[T, T], comp.__split__(ratio))


def split_to_first(comp: T, ratio: float) -> tuple[T | None, None]:
    """Give component to first entity only.

    Args:
        comp: Component to assign.
        ratio: Split ratio (ignored).

    Returns:
        Tuple of (comp, None).
    """
    return (comp, None)


def split_to_both(comp: T, ratio: float) -> tuple[T, T]:
    """Clone component to both entities.

    Args:
        comp: Component to clone.
        ratio: Split ratio (ignored).

    Returns:
        Tuple of (deep_copy1, deep_copy2).
    """
    return (copy.deepcopy(comp), copy.deepcopy(comp))


def split_skip(comp: T, ratio: float) -> tuple[None, None]:
    """Skip component (exclude from both split entities).

    Args:
        comp: Component (ignored).
        ratio: Split ratio (ignored).

    Returns:
        Tuple of (None, None) to indicate component should be skipped.
    """
    return (None, None)


def split_error(comp: T, ratio: float) -> tuple[T, T]:
    """Raise an error for non-splittable components.

    Args:
        comp: Component.
        ratio: Split ratio (ignored).

    Returns:
        Never returns.

    Raises:
        TypeError: Always raised to indicate incompatible component.
    """
    raise TypeError(f"Component {type(comp).__name__} is not Splittable and strategy is ERROR")
