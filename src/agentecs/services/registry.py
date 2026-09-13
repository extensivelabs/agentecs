"""Component type registry."""

from __future__ import annotations

from agentecs.functions.component import stable_component_type_id
from agentecs.models.component import ComponentTypeMeta


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

        component_type_id = stable_component_type_id(cls)

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


_registry = ComponentRegistry()


def get_registry() -> ComponentRegistry:
    """Access the global component registry.

    Returns:
        The process-local ComponentRegistry instance.
    """
    return _registry
