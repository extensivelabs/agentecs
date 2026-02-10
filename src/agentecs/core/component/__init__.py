"""Component functionality: models, registry, decorator, and operations."""

from agentecs.core.component.core import (
    ComponentRegistry,
    component,
    get_registry,
    merge_components,
    reduce_components,
)
from agentecs.core.component.models import (
    ComponentRef,
    ComponentTypeMeta,
    Diffable,
    Interpolatable,
    Mergeable,
    NonMergeableHandling,
    NonSplittableHandling,
    Reducible,
    Splittable,
)
from agentecs.core.component.wrapper import Shared

__all__ = [
    # Models
    "ComponentTypeMeta",
    "Mergeable",
    "Splittable",
    "Reducible",
    "Diffable",
    "Interpolatable",
    "NonMergeableHandling",
    "NonSplittableHandling",
    "ComponentRef",
    # Core
    "component",
    "get_registry",
    "ComponentRegistry",
    "merge_components",
    "reduce_components",
    "Shared",
]
