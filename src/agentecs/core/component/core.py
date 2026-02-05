"""Component registry, decorator, and operations.

Usage:
    @component
    @dataclass(slots=True)
    class Position:
        x: float
        y: float

    # With merge support:
    @component
    @dataclass
    class Context:
        history: list[str]

        def __merge__(self, other: "Context") -> "Context":
            return Context(history=self.history + other.history)
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import is_dataclass
from typing import TypeVar

from agentecs.core.component.models import ComponentMeta, Mergeable, Reducible

T = TypeVar("T")


def _stable_component_id(cls: type) -> int:
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


class ComponentRegistry:
    """Process-local registry mapping component types to deterministic IDs.

    Maintains bidirectional mapping between component types and their IDs.
    Deterministic IDs ensure same code produces same IDs across nodes.

    # TODO: Figure our distributed syncing of local registrys if needed.
    """

    def __init__(self) -> None:
        """Initialize empty component registry."""
        self._by_type: dict[type, ComponentMeta] = {}
        self._by_id: dict[int, type] = {}

    def register(self, cls: type) -> ComponentMeta:
        """Register a component type and return its metadata.

        Args:
            cls: Component class to register.

        Returns:
            Component metadata including ID and type name.

        Raises:
            RuntimeError: If component ID collides with another registered type.
        """
        if cls in self._by_type:
            return self._by_type[cls]

        component_id = _stable_component_id(cls)

        if component_id in self._by_id:
            existing = self._by_id[component_id]
            raise RuntimeError(
                f"Component ID collision: {cls} and {existing} hash to {component_id}"
            )

        meta = ComponentMeta(
            component_id=component_id,
            type_name=f"{cls.__module__}.{cls.__qualname__}",
        )
        self._by_type[cls] = meta
        self._by_id[component_id] = cls
        return meta

    def get_meta(self, cls: type) -> ComponentMeta | None:
        """Get metadata for a registered component type.

        Args:
            cls: Component class to look up.

        Returns:
            Component metadata if registered, None otherwise.
        """
        return self._by_type.get(cls)

    def get_type(self, component_id: int) -> type | None:
        """Get component type by its ID.

        Args:
            component_id: Component ID to look up.

        Returns:
            Component class if found, None otherwise.
        """
        return self._by_id.get(component_id)

    def is_registered(self, cls: type) -> bool:
        """Check if a type is registered as a component.

        Args:
            cls: Class to check.

        Returns:
            True if class is registered as component, False otherwise.
        """
        return cls in self._by_type


# Module-level registry instance
_registry = ComponentRegistry()


def get_registry() -> ComponentRegistry:
    """Access the global component registry.

    Returns:
        The process-local ComponentRegistry instance.
    """
    return _registry


def _is_pydantic(cls: type) -> bool:
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


def component(cls: type) -> type:
    """Register a dataclass or Pydantic model as a component type.

    Args:
        cls: Dataclass or Pydantic model to register as component.

    Returns:
        The decorated class with __component_meta__ attribute added.

    Raises:
        TypeError: If class is neither a dataclass nor Pydantic model.

    Note:
        Apply @component AFTER @dataclass:

        >>> @component
        ... @dataclass(slots=True)
        ... class MyComponent:
        ...     value: int
    """
    if not (is_dataclass(cls) or _is_pydantic(cls)):
        raise TypeError(
            f"Component {cls.__name__} must be a dataclass or Pydantic model. "
            f"Did you forget @dataclass decorator?"
        )

    meta = _registry.register(cls)
    cls.__component_meta__ = meta  # type: ignore
    return cls


def merge_components(a: T, b: T, strategy: Callable[[T, T], T] | None = None) -> T:
    """Merge two components using custom strategy or component's __merge__ method.

    Args:
        a: First component instance.
        b: Second component instance (must be same type as a).
        strategy: Optional custom merge function. If None, uses a.__merge__(b).

    Returns:
        Merged component instance.

    Raises:
        TypeError: If component doesn't implement Mergeable and no strategy provided.
    """
    if strategy:
        return strategy(a, b)
    if isinstance(a, Mergeable):
        # a and b are same type T, and a is Mergeable, so b is too
        # __merge__ uses Self type annotation, returns same type
        return a.__merge__(b)
    raise TypeError(f"{type(a).__name__} is not Mergeable and no strategy provided")


def reduce_components(items: list[T], strategy: Callable[[list[T]], T] | None = None) -> T:
    """Reduce N components to one using strategy, __reduce_many__, or sequential merge.

    Tries in order:
    1. Custom strategy function if provided
    2. Class __reduce_many__ method if component implements Reducible
    3. Sequential pairwise merge using __merge__

    Args:
        items: List of component instances to reduce (must all be same type).
        strategy: Optional custom reduction function.

    Returns:
        Single reduced component instance.

    Raises:
        ValueError: If items list is empty.
        TypeError: If components don't implement Mergeable/Reducible and no strategy.
    """
    if not items:
        raise ValueError("Cannot reduce empty list")
    if len(items) == 1:
        return items[0]

    if strategy:
        return strategy(items)

    cls = type(items[0])
    if isinstance(cls, type) and issubclass(cls, Reducible):
        return cls.__reduce_many__(items)  # type: ignore

    # Fallback to sequential merge
    result = items[0]
    for item in items[1:]:
        result = merge_components(result, item)
    return result
