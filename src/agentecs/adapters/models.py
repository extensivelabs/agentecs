"""Data models for adapters.

Defines types used by VectorStore and LLMClient protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class SearchMode(Enum):
    """Search mode for vector store queries."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass(slots=True)
class SearchResult(Generic[T]):
    """Result from a vector store search.

    Attributes:
        id: Document identifier.
        data: The typed data model.
        score: Similarity/relevance score (higher is better, normalized 0-1 for cosine).
        distance: Raw distance value (lower is better).
    """

    id: str
    data: T
    score: float
    distance: float | None = None


@dataclass(slots=True)
class VectorStoreItem(Generic[T]):
    """Item to add to vector store.

    Attributes:
        id: Unique identifier for the item.
        embedding: Vector embedding.
        text: Text content for keyword search.
        data: The typed data model to store.
    """

    id: str
    embedding: list[float]
    text: str
    data: T


class FilterOperator(Enum):
    """Operators for metadata filtering."""

    EQ = "eq"  # equals
    NE = "ne"  # not equals
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal
    IN = "in"  # in list
    NIN = "nin"  # not in list
    CONTAINS = "contains"  # string contains


@dataclass(slots=True)
class Filter:
    """Single filter condition.

    Attributes:
        field: Field name to filter on (supports nested: "metadata.category").
        operator: Comparison operator.
        value: Value to compare against.
    """

    field: str
    operator: FilterOperator
    value: Any


@dataclass(slots=True)
class FilterGroup:
    """Group of filters combined with AND/OR.

    Attributes:
        filters: List of Filter or nested FilterGroup.
        operator: How to combine filters ("and" or "or").
    """

    filters: list[Filter | FilterGroup] = field(default_factory=list)
    operator: str = "and"  # "and" or "or"


class MessageRole(Enum):
    """Role of a message in LLM conversation."""

    SYSTEM = "developer"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True)
class Message:
    """A message in an LLM conversation.

    Attributes:
        role: Who sent the message.
        content: Message text content.
    """

    role: MessageRole
    content: str

    @classmethod
    def system(cls, content: str) -> Message:
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> Message:
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> Message:
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)
