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
from agentecs.core.component.operations import (
    combine_protocol_or_fallback,
    reduce_components,
    split_protocol_or_fallback,
)
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
    "combine_protocol_or_fallback",
    "split_protocol_or_fallback",
    "reduce_components",
    "Shared",
]
