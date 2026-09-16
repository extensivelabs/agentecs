"""Data models: frozen dataclasses, enums, and plain value types."""

from agentecs.models.component import (
    Combinable,
    ComponentRef,
    ComponentTypeMeta,
    ComponentWrapper,
    Shared,
    Splittable,
    WrappedComponent,
    get_component,
    get_type,
)
from agentecs.models.errors import AccessViolationError, ConflictError
from agentecs.models.identity import AllocatorState, EntityId, SystemEntity
from agentecs.models.llm import Message, MessageRole
from agentecs.models.query import (
    AccessPattern,
    AllAccess,
    NoAccess,
    Query,
    QueryAccess,
    TypeAccess,
)
from agentecs.models.result import MutationOp, OpKind, SystemResult, SystemReturn
from agentecs.models.scheduling import (
    ExecutionGroup,
    ExecutionPlan,
    RetryPolicy,
    SchedulerConfig,
)
from agentecs.models.system import Access, SystemDescriptor, SystemMode
from agentecs.models.tracing import TickRecord
from agentecs.models.types import Copy
from agentecs.models.vectorstore import (
    Filter,
    FilterGroup,
    FilterOperator,
    SearchMode,
    SearchResult,
    VectorStoreItem,
)

__all__ = [
    # Component
    "Combinable",
    "ComponentRef",
    "ComponentTypeMeta",
    "ComponentWrapper",
    "Shared",
    "Splittable",
    "WrappedComponent",
    "get_component",
    "get_type",
    # Errors
    "AccessViolationError",
    "ConflictError",
    # Identity
    "AllocatorState",
    "EntityId",
    "SystemEntity",
    # LLM
    "Message",
    "MessageRole",
    # Query
    "AccessPattern",
    "AllAccess",
    "NoAccess",
    "Query",
    "QueryAccess",
    "TypeAccess",
    # Result
    "MutationOp",
    "OpKind",
    "SystemResult",
    "SystemReturn",
    # Scheduling
    "ExecutionGroup",
    "ExecutionPlan",
    "RetryPolicy",
    "SchedulerConfig",
    # System
    "Access",
    "SystemDescriptor",
    "SystemMode",
    # Tracing
    "TickRecord",
    # Types
    "Copy",
    # Vector store
    "Filter",
    "FilterGroup",
    "FilterOperator",
    "SearchMode",
    "SearchResult",
    "VectorStoreItem",
]
