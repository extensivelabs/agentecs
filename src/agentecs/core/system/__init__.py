"""System functionality: decorators, descriptors, and access control."""

from agentecs.core.system.core import check_read_access, check_write_access, system
from agentecs.core.system.models import Access, ExecutionStrategy, SystemDescriptor, SystemMode

__all__ = [
    # Models
    "SystemDescriptor",
    "SystemMode",
    "Access",
    "ExecutionStrategy",
    # Core
    "system",
    "check_read_access",
    "check_write_access",
]
