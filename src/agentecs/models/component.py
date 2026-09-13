"""Component models: protocols and metadata.

Component operation protocols are optional interfaces that components can implement
to support advanced operations like merging, splitting, and interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Self, runtime_checkable


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


class ComponentWrapper[T]:
    """Base class for component wrappers that modify storage semantics."""

    __slots__ = ("_component",)

    def __init__(self, component: T) -> None:
        self._component = component

    def unwrap(self) -> T:
        """Return the original component instance."""
        return self._component

    @property
    def component_type(self) -> type[T]:
        """Return the type of the wrapped component."""
        return type(self._component)


class Shared[T](ComponentWrapper[T]):
    """Wrapper for shared components, adding a UUID reference."""

    __slots__ = ("_ref",)

    def __init__(self, component: T) -> None:
        super().__init__(component)
        self._ref: ComponentRef = ComponentRef(
            instance_id=id(component), component_type=type(component)
        )

    @property
    def ref_id(self) -> int:
        """Return the unique reference ID for this shared component."""
        return self._ref.instance_id


# Type variable for wrapped components (Shared, Owned, ...)
WrappedComponent = Shared  # | Owned | ... (future wrappers can be added here)


def get_type(component: Any | WrappedComponent[Any]) -> type:
    """Get the underlying component type, unwrapping if necessary."""
    if isinstance(component, WrappedComponent):
        return component.component_type
    return type(component)


def get_component(component: Any | WrappedComponent[Any]) -> Any:
    """Get the underlying component instance, unwrapping if necessary."""
    if isinstance(component, WrappedComponent):
        return component.unwrap()
    return component
