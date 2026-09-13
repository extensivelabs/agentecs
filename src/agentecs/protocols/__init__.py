"""Structural protocols defining the framework's seams."""

from agentecs.protocols.access import ReadOnlyAccess
from agentecs.protocols.execution import (
    ExecutionGroupBuilder,
    ExecutionStrategy,
    SystemExecutor,
)
from agentecs.protocols.history import HistoryStore
from agentecs.protocols.llm import LLMClient
from agentecs.protocols.storage import Storage
from agentecs.protocols.vectorstore import VectorStore

__all__ = [
    "ExecutionGroupBuilder",
    "ExecutionStrategy",
    "HistoryStore",
    "LLMClient",
    "ReadOnlyAccess",
    "Storage",
    "SystemExecutor",
    "VectorStore",
]
