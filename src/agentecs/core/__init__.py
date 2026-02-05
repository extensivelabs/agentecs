"""Core functionalities: stateless, SOLID protocols and primitives.

Architecture Note:
    core/ contains pure, stateless functionalities following SOLID principles.
    These are general-purpose building blocks with no runtime state mutation.
    For stateful services, see world/, storage/, and scheduling/.
"""

from agentecs.core.component import (
    ComponentMeta,
    ComponentRegistry,
    Diffable,
    Interpolatable,
    Mergeable,
    NonMergeableHandling,
    NonSplittableHandling,
    Reducible,
    Splittable,
    component,
    get_registry,
    merge_components,
    reduce_components,
)
from agentecs.core.identity import EntityId, SystemEntity
from agentecs.core.query import (
    AccessPattern,
    AllAccess,
    Query,
    QueryAccess,
    TypeAccess,
    normalize_access,
    queries_disjoint,
)
from agentecs.core.system import (
    Access,
    SystemDescriptor,
    SystemMode,
    check_read_access,
    check_write_access,
    system,
)
from agentecs.core.types import Copy

__all__ = [
    # Types
    "Copy",
    # Identity
    "EntityId",
    "SystemEntity",
    # Component
    "component",
    "get_registry",
    "ComponentMeta",
    "ComponentRegistry",
    "Mergeable",
    "Splittable",
    "Reducible",
    "Diffable",
    "Interpolatable",
    "NonMergeableHandling",
    "NonSplittableHandling",
    "merge_components",
    "reduce_components",
    # System
    "system",
    "SystemDescriptor",
    "SystemMode",
    "Access",
    "check_read_access",
    "check_write_access",
    # Query
    "Query",
    "AccessPattern",
    "AllAccess",
    "TypeAccess",
    "QueryAccess",
    "queries_disjoint",
    "normalize_access",
]
