"""Component functionality: models, registry, decorator, and operations."""

from agentecs.core.component.core import (
    ComponentRegistry,
    component,
    get_registry,
)
from agentecs.core.component.models import (
    Combinable,
    ComponentRef,
    ComponentTypeMeta,
    Splittable,
)
from agentecs.core.component.operations import reduce_components
from agentecs.core.component.wrapper import Shared

__all__ = [
    # Models
    "ComponentTypeMeta",
    "Splittable",
    "Combinable",
    "ComponentRef",
    # Core
    "component",
    "get_registry",
    "ComponentRegistry",
    "reduce_components",
    "Shared",
]
