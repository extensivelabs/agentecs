"""External integration adapters.

Provides protocols and implementations for:
- VectorStore: Vector database / RAG operations
- LLMClient: LLM with structured output

Usage:
    from agentecs.adapters import VectorStore, LLMClient, SearchMode, Message

    # Implementations (require optional dependencies)
    from agentecs.adapters.chroma import ChromaAdapter  # pip install agentecs[chroma]
    from agentecs.adapters.instructor import InstructorAdapter  # pip install agentecs[llm]
"""

from agentecs.adapters.models import (
    Filter,
    FilterGroup,
    FilterOperator,
    Message,
    MessageRole,
    SearchMode,
    SearchResult,
    VectorStoreItem,
)
from agentecs.adapters.protocol import LLMClient, VectorStore

__all__ = [
    # Protocols
    "VectorStore",
    "LLMClient",
    # VectorStore types
    "SearchMode",
    "SearchResult",
    "VectorStoreItem",
    "Filter",
    "FilterGroup",
    "FilterOperator",
    # LLM types
    "Message",
    "MessageRole",
]
