"""Adapter protocols for external integrations.

Defines interfaces for VectorStore and LLMClient adapters.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol, TypeVar, runtime_checkable

from agentecs.adapters.models import (
    Filter,
    FilterGroup,
    Message,
    SearchMode,
    SearchResult,
    VectorStoreItem,
)

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class VectorStore(Protocol[T]):
    """Protocol for vector database operations with typed data models.

    Generic type T represents the data model (Pydantic model or dataclass)
    that will be stored alongside vectors.

    Usage:
        @dataclass
        class Document:
            title: str
            content: str

        store: VectorStore[Document] = ChromaAdapter.from_memory("docs", Document)
        store.add("doc1", embedding=[...], text="...", data=Document(...))
        results = store.search(query_embedding=[...], mode=SearchMode.HYBRID)
    """

    def add(
        self,
        id: str,
        embedding: list[float],
        text: str,
        data: T,
    ) -> str:
        """Add a single item to the store.

        Args:
            id: Unique identifier for the item.
            embedding: Vector embedding.
            text: Text content for keyword search.
            data: Typed data model to store.

        Returns:
            The ID of the added item.
        """
        ...

    def add_batch(self, items: list[VectorStoreItem[T]]) -> list[str]:
        """Add multiple items to the store.

        Args:
            items: List of items to add.

        Returns:
            List of IDs for added items.
        """
        ...

    def get(self, id: str) -> T | None:
        """Get an item by ID.

        Args:
            id: Item identifier.

        Returns:
            The data model if found, None otherwise.
        """
        ...

    def get_batch(self, ids: list[str]) -> list[T | None]:
        """Get multiple items by ID.

        Args:
            ids: List of item identifiers.

        Returns:
            List of data models (None for missing items).
        """
        ...

    def update(
        self,
        id: str,
        embedding: list[float] | None = None,
        text: str | None = None,
        data: T | None = None,
    ) -> bool:
        """Update an existing item.

        Args:
            id: Item identifier.
            embedding: New embedding (optional).
            text: New text (optional).
            data: New data model (optional).

        Returns:
            True if item existed and was updated.
        """
        ...

    def delete(self, id: str) -> bool:
        """Delete an item.

        Args:
            id: Item identifier.

        Returns:
            True if item existed and was deleted.
        """
        ...

    def delete_batch(self, ids: list[str]) -> int:
        """Delete multiple items.

        Args:
            ids: List of item identifiers.

        Returns:
            Number of items deleted.
        """
        ...

    def search(
        self,
        query_embedding: list[float] | None = None,
        query_text: str | None = None,
        mode: SearchMode = SearchMode.VECTOR,
        filters: Filter | FilterGroup | None = None,
        limit: int = 10,
    ) -> list[SearchResult[T]]:
        """Search the store.

        Args:
            query_embedding: Query vector for vector/hybrid search.
            query_text: Query text for keyword/hybrid search.
            mode: Search mode (vector, keyword, or hybrid).
            filters: Optional metadata filters.
            limit: Maximum number of results.

        Returns:
            List of search results with scores.
        """
        ...

    def count(self) -> int:
        """Get total number of items in the store.

        Returns:
            Item count.
        """
        ...

    # Async variants

    async def add_async(
        self,
        id: str,
        embedding: list[float],
        text: str,
        data: T,
    ) -> str:
        """Add a single item to the store (async).

        Args:
            id: Unique identifier for the item.
            embedding: Vector embedding.
            text: Text content for keyword search.
            data: Typed data model to store.

        Returns:
            The ID of the added item.
        """
        ...

    async def add_batch_async(self, items: list[VectorStoreItem[T]]) -> list[str]:
        """Add multiple items to the store (async).

        Args:
            items: List of items to add.

        Returns:
            List of IDs for added items.
        """
        ...

    async def get_async(self, id: str) -> T | None:
        """Get an item by ID (async).

        Args:
            id: Item identifier.

        Returns:
            The data model if found, None otherwise.
        """
        ...

    async def search_async(
        self,
        query_embedding: list[float] | None = None,
        query_text: str | None = None,
        mode: SearchMode = SearchMode.VECTOR,
        filters: Filter | FilterGroup | None = None,
        limit: int = 10,
    ) -> list[SearchResult[T]]:
        """Search the store (async).

        Args:
            query_embedding: Query vector for vector/hybrid search.
            query_text: Query text for keyword/hybrid search.
            mode: Search mode (vector, keyword, or hybrid).
            filters: Optional metadata filters.
            limit: Maximum number of results.

        Returns:
            List of search results with scores.
        """
        ...


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM operations with structured output.

    Uses Pydantic models for type-safe responses.

    Usage:
        class Analysis(BaseModel):
            sentiment: str
            confidence: float

        client: LLMClient = InstructorAdapter.from_openai_client(openai_client)
        result: Analysis = client.call(messages, response_model=Analysis)
    """

    def call(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Call LLM with structured output.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Validated response as the specified model type.
        """
        ...

    async def call_async(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> T:
        """Call LLM with structured output (async).

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Validated response as the specified model type.
        """
        ...

    def stream(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Iterator[T]:
        """Stream LLM response with partial structured output.

        Yields partial objects as they are received, with fields
        populated incrementally.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Partial response objects with incrementally populated fields.
        """
        ...

    def stream_async(
        self,
        messages: list[Message],
        response_model: type[T],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Stream LLM response with partial structured output (async).

        Yields partial objects as they are received, with fields
        populated incrementally.

        Args:
            messages: Conversation messages.
            response_model: Pydantic model for response validation.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            **kwargs: Additional provider-specific parameters.

        Yields:
            Partial response objects with incrementally populated fields.
        """
        ...
