"""Component models: protocols and metadata.

Component operation protocols are optional interfaces that components can implement
to support advanced operations like merging, splitting, and interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class Combinable(Protocol):
    """Component knows how to accumulate multiple writes.

    When multiple ops target the same (entity, type), the framework
    folds them with __combine__ instead of overwriting.
    """

    def __combine__(self, other: Self) -> Self: ...


@runtime_checkable
class Splittable(Protocol):
    """One instance → two instances (for agent splitting)."""

    def __split__(self) -> tuple[Self, Self]: ...


@dataclass(slots=True, frozen=True)
class ComponentTypeMeta:
    """Metadata for registered component types."""

    component_type_id: int
    type_name: str


@dataclass(slots=True)
class ComponentRef:
    """Tracks a shared component."""

    instance_id: int
    component_type: type
