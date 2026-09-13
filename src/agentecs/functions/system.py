"""Access checks against a system's declared read/write contract."""

from __future__ import annotations

from agentecs.models.system import SystemDescriptor, SystemMode


def check_read_access(
    descriptor: SystemDescriptor,
    component_type: type,
) -> bool:
    """Check if system is allowed to read this component type."""
    if descriptor.is_dev_mode():
        return True
    return descriptor.can_read_type(component_type)


def check_write_access(
    descriptor: SystemDescriptor,
    component_type: type,
) -> bool:
    """Check if system is allowed to write this component type."""
    if descriptor.is_dev_mode():
        return True
    if descriptor.mode == SystemMode.READONLY:
        return False
    return descriptor.can_write_type(component_type)
