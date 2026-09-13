"""Local storage service: component storage plus the entity ID allocator."""

from agentecs.services.storage.allocator import EntityAllocator
from agentecs.services.storage.local import LocalStorage

__all__ = [
    "EntityAllocator",
    "LocalStorage",
]
