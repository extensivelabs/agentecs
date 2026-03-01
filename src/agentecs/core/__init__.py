"""Core functionalities: stateless, SOLID protocols and primitives.

Architecture Note:
    core/ contains pure, stateless functionalities following SOLID principles.
    These are general-purpose building blocks with no runtime state mutation.
    For stateful services, see world/, storage/, and scheduling/.
"""

from agentecs.core.component import (
    Combinable,
    ComponentRef,
    ComponentRegistry,
    ComponentTypeMeta,
    Shared,
    Splittable,
    component,
    get_registry,
    reduce_components,
)
from agentecs.core.identity import EntityId, SystemEntity
from agentecs.core.query import (
    AccessPattern,
    AllAccess,
    NoAccess,
    Query,
    QueryAccess,
    TypeAccess,
    normalize_access,
    normalize_reads_and_writes,
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
    "ComponentTypeMeta",
    "ComponentRegistry",
    "Combinable",
    "Splittable",
    "reduce_components",
    "Shared",
    "ComponentRef",
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
    "NoAccess",
    "TypeAccess",
    "QueryAccess",
    "queries_disjoint",
    "normalize_access",
    "normalize_reads_and_writes",
]
