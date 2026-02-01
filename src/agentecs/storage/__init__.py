"""Storage backends."""

from agentecs.storage.local import LocalStorage
from agentecs.storage.protocol import Storage

__all__ = [
    "Storage",
    "LocalStorage",
]
