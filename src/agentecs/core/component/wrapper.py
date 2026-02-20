from __future__ import annotations

from typing import Any

from agentecs.core.component.models import ComponentRef


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
