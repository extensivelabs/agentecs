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
from typing import overload

from agentecs.core.component.models import ComponentTypeMeta


def _stable_component_type_id(cls: type) -> int:
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
    """Process-local registry mapping component types to deterministic type IDs.

    Maintains bidirectional mapping between component types and their type IDs.
    Deterministic IDs ensure same code produces same IDs across nodes.

    # TODO: Figure out distributed syncing of local registries if needed.
    """

    def __init__(self) -> None:
        """Initialize empty component registry."""
        self._by_type: dict[type, ComponentTypeMeta] = {}
        self._by_type_id: dict[int, type] = {}

    def register(self, cls: type) -> ComponentTypeMeta:
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

        component_type_id = _stable_component_type_id(cls)

        if component_type_id in self._by_type_id:
            existing = self._by_type_id[component_type_id]
            raise RuntimeError(
                f"Component ID collision: {cls} and {existing} hash to {component_type_id}"
            )

        meta = ComponentTypeMeta(
            component_type_id=component_type_id,
            type_name=f"{cls.__module__}.{cls.__qualname__}",
        )
        self._by_type[cls] = meta
        self._by_type_id[component_type_id] = cls
        return meta

    def get_meta(self, cls: type) -> ComponentTypeMeta | None:
        """Get metadata for a registered component type.

        Args:
            cls: Component class to look up.

        Returns:
            Component metadata if registered, None otherwise.
        """
        return self._by_type.get(cls)

    def get_type(self, component_type_id: int) -> type | None:
        """Get component type by its type ID.

        Args:
            component_type_id: Component type ID to look up.

        Returns:
            Component class if found, None otherwise.
        """
        return self._by_type_id.get(component_type_id)

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


@overload
def component(cls: type) -> type: ...


@overload
def component(cls: None = None) -> Callable[[type], type]: ...


def component(cls: type | None = None) -> type | Callable[[type], type]:
    """Register a dataclass or Pydantic model as a component type.

    Supports two forms:
        @component                    # bare decorator
        @component()                  # parenthesized, no args

    Args:
        cls: The class to register, or None if called with arguments.

    Returns:
        Decorated class or decorator function.

    Raises:
        TypeError: If class is neither a dataclass nor Pydantic model.

    Note:
        Apply @component AFTER @dataclass:

        >>> @component
        ... @dataclass(slots=True)
        ... class MyComponent:
        ...     value: int
    """

    def decorator(c: type) -> type:
        if not (is_dataclass(c) or _is_pydantic(c)):
            raise TypeError(
                f"Component {c.__name__} must be a dataclass or Pydantic model. "
                f"Did you forget @dataclass decorator?"
            )
        meta = _registry.register(c)
        c.__component_meta__ = meta  # type: ignore
        return c

    if cls is None:
        # Called with args: @component()
        return decorator
    else:
        # Called bare: @component
        return decorator(cls)
