"""Component functionality: models, registry, decorator, and operations."""

from agentecs.core.component.core import (
    ComponentRegistry,
    component,
    get_registry,
    merge_components,
    reduce_components,
)
from agentecs.core.component.models import (
    ComponentMeta,
    Diffable,
    Interpolatable,
    Mergeable,
    NonMergeableHandling,
    NonSplittableHandling,
    Reducible,
    Splittable,
)

__all__ = [
    # Models
    "ComponentMeta",
    "Mergeable",
    "Splittable",
    "Reducible",
    "Diffable",
    "Interpolatable",
    "NonMergeableHandling",
    "NonSplittableHandling",
    # Core
    "component",
    "get_registry",
    "ComponentRegistry",
    "merge_components",
    "reduce_components",
]
