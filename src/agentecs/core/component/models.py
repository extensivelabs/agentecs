"""Component models: protocols and metadata.

Component operation protocols are optional interfaces that components can implement
to support advanced operations like merging, splitting, and interpolation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Protocol, Self, TypeVar, runtime_checkable

T = TypeVar("T")


class NonMergeableHandling(Enum):
    """Strategy for handling non-mergeable components during entity merge."""

    ERROR = auto()  # Raise error if component not Mergeable
    FIRST = auto()  # Keep component from first entity
    SECOND = auto()  # Keep component from second entity
    SKIP = auto()  # Don't include in merged entity

    def get_strategy(self) -> Callable[[T, T], T | None]:
        """Get the merge strategy function for this handling mode.

        Returns:
            Pure function implementing the merge strategy.
        """
        # Late import to avoid circular dependency
        from agentecs.core.component import operations

        strategies = {
            NonMergeableHandling.ERROR: operations.merge_error,
            NonMergeableHandling.FIRST: operations.merge_take_first,
            NonMergeableHandling.SECOND: operations.merge_take_second,
            NonMergeableHandling.SKIP: operations.merge_skip,
        }
        return strategies[self]


class NonSplittableHandling(Enum):
    """Strategy for handling non-splittable components during entity split."""

    ERROR = auto()  # Raise error if component not Splittable
    FIRST = auto()  # Give component to first entity only
    BOTH = auto()  # Clone component to both entities
    SKIP = auto()  # Don't include in either entity

    def get_strategy(self) -> Callable[[T, float], tuple[T | None, T | None]]:
        """Get the split strategy function for this handling mode.

        Returns:
            Pure function implementing the split strategy.
        """
        # Late import to avoid circular dependency
        from agentecs.core.component import operations

        strategies = {
            NonSplittableHandling.ERROR: operations.split_error,
            NonSplittableHandling.FIRST: operations.split_to_first,
            NonSplittableHandling.BOTH: operations.split_to_both,
            NonSplittableHandling.SKIP: operations.split_skip,
        }
        return strategies[self]


@runtime_checkable
class Mergeable(Protocol):
    """Two instances → one combined instance."""

    def __merge__(self, other: Any) -> Self: ...


@runtime_checkable
class Splittable(Protocol):
    """One instance → two instances (for agent splitting)."""

    def __split__(self, ratio: float = 0.5) -> tuple[Self, Self]: ...


@runtime_checkable
class Reducible(Protocol):
    """N instances → one instance (for aggregation)."""

    @classmethod
    def __reduce_many__(cls, items: list[Self]) -> Self: ...


@runtime_checkable
class Diffable(Protocol):
    """Compute delta between instances (for sync/replication)."""

    def __diff__(self, baseline: Self) -> Self: ...
    def __apply_diff__(self, diff: Self) -> Self: ...


@runtime_checkable
class Interpolatable(Protocol):
    """Blend between instances (for continuous transitions)."""

    def __interpolate__(self, other: Self, t: float) -> Self: ...


@dataclass(slots=True, frozen=True)
class ComponentTypeMeta:
    """Metadata for registered component types."""

    component_type_id: int
    type_name: str
    shared: bool


@dataclass(slots=True)
class ComponentRef:
    """Tracks a shared component."""

    instance_id: int
    component_type: type
