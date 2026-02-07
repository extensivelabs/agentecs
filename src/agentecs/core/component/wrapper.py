from __future__ import annotations

from uuid import UUID

from agentecs.core.component.models import ComponentRef


class _ComponentWrapper[T]:
    """Base class for component wrappers that modify storage semantics."""

    __slots__ = ("_component",)

    def __init__(self, component: T) -> None:
        self._component = component

    def unwrap(self) -> T:
        return self._component

    @property
    def component_type(self) -> type[T]:
        return type(self._component)


class Shared[T](_ComponentWrapper[T]):
    """Wrapper for shared components, adding a UUID reference."""

    __slots__ = ("_ref",)

    def __init__(self, component: T) -> None:
        super().__init__(component)
        self._ref: ComponentRef = ComponentRef(
            instance_id=UUID(int=id(component)), component_type=type(component)
        )

    @property
    def ref_id(self) -> UUID:
        """Return the unique reference ID for this shared component."""
        return self._ref.instance_id


# Type variable for wrapped components (Shared, Owned, ...)
WrappedComponent = Shared  # | Owned | ... (future wrappers can be added here)
