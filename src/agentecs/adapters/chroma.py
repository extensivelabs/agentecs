"""ChromaDB adapter implementing VectorStore protocol.

Provides typed vector storage using ChromaDB with automatic
serialization of Pydantic models and dataclasses.

Usage:
    from dataclasses import dataclass
    from agentecs.adapters.chroma import ChromaAdapter

    @dataclass
    class Document:
        title: str
        content: str

    # Ephemeral (in-memory)
    store = ChromaAdapter.from_memory("docs", Document)

    # Persistent
    store = ChromaAdapter.from_path("./chroma_data", "docs", Document)

    # Add documents
    store.add("doc1", embedding=[0.1, 0.2, ...], text="Hello", data=Document("Title", "Content"))

    # Search
    results = store.search(query_embedding=[0.1, 0.2, ...], limit=5)
    for r in results:
        print(r.data.title, r.score)  # Typed as Document
"""

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING, Any, TypeVar, get_type_hints

from agentecs.adapters.models import (
    Filter,
    FilterGroup,
    FilterOperator,
    SearchMode,
    SearchResult,
    VectorStoreItem,
)

if TYPE_CHECKING:
    import chromadb
    from chromadb.api.models.Collection import Collection

T = TypeVar("T")

# Reserved metadata keys used internally
_RESERVED_KEYS = {"_type", "_json"}


def _is_pydantic_model(cls: type[Any]) -> bool:
    """Check if class is a Pydantic model."""
    try:
        from pydantic import BaseModel

        return isinstance(cls, type) and issubclass(cls, BaseModel)
    except ImportError:
        return False


def _is_dataclass(cls: type) -> bool:
    """Check if class is a dataclass."""
    return dataclasses.is_dataclass(cls) and isinstance(cls, type)


def _serialize_to_metadata[T](data: Any, data_type: type[T]) -> dict[str, Any]:
    """Serialize a Pydantic model or dataclass to ChromaDB metadata.

    ChromaDB metadata only supports str, int, float, bool values.
    Complex nested structures are JSON-serialized.

    Args:
        data: The data model instance.
        data_type: The type of the data model.

    Returns:
        Dictionary suitable for ChromaDB metadata.
    """
    metadata: dict[str, Any] = {"_type": f"{data_type.__module__}.{data_type.__qualname__}"}

    if _is_pydantic_model(data_type):
        # Pydantic model - use model_dump
        raw = data.model_dump()
    elif _is_dataclass(data_type):
        # Dataclass - use asdict
        raw = dataclasses.asdict(data)
    else:
        # Fallback - store as JSON string
        metadata["_json"] = json.dumps(data) if not isinstance(data, str) else data
        return metadata

    # Flatten simple values, JSON-serialize complex ones
    for key, value in raw.items():
        if key in _RESERVED_KEYS:
            continue
        if isinstance(value, str | int | float | bool):
            metadata[key] = value
        elif value is None:
            # ChromaDB doesn't support None, skip or use sentinel
            metadata[f"_null_{key}"] = True
        else:
            # Complex value - JSON serialize
            metadata[f"_json_{key}"] = json.dumps(value)

    return metadata


def _deserialize_from_metadata[T](metadata: dict[str, Any], data_type: type[T]) -> T:
    """Deserialize ChromaDB metadata back to a Pydantic model or dataclass.

    Args:
        metadata: ChromaDB metadata dictionary.
        data_type: The type to deserialize to.

    Returns:
        Instance of the data type.
    """
    # Check for direct JSON storage
    if "_json" in metadata:
        raw = json.loads(metadata["_json"])
        if _is_pydantic_model(data_type):
            # Pydantic model - use model_validate
            return data_type.model_validate(raw)  # type: ignore[attr-defined,no-any-return]
        elif _is_dataclass(data_type):
            return data_type(**raw)
        return raw  # type: ignore[no-any-return]

    # Reconstruct from flattened metadata
    reconstructed: dict[str, Any] = {}

    # Get type hints to know expected fields
    if _is_pydantic_model(data_type):
        field_names = set(data_type.model_fields.keys())  # type: ignore[attr-defined]
    elif _is_dataclass(data_type):
        field_names = {f.name for f in dataclasses.fields(data_type)}  # type: ignore[arg-type]
    else:
        field_names = set(get_type_hints(data_type).keys())

    for key, value in metadata.items():
        if key.startswith("_"):
            # Handle special keys
            if key.startswith("_null_"):
                field_name = key[6:]
                if field_name in field_names:
                    reconstructed[field_name] = None
            elif key.startswith("_json_"):
                field_name = key[6:]
                if field_name in field_names:
                    reconstructed[field_name] = json.loads(value)
        elif key in field_names:
            reconstructed[key] = value

    if _is_pydantic_model(data_type):
        return data_type.model_validate(reconstructed)  # type: ignore[attr-defined,no-any-return]
    elif _is_dataclass(data_type):
        return data_type(**reconstructed)

    # Fallback - try direct instantiation
    return data_type(**reconstructed)


def _build_chroma_where(filters: Filter | FilterGroup | None) -> dict[str, Any] | None:
    """Convert Filter/FilterGroup to ChromaDB where clause.

    Args:
        filters: Filter specification.

    Returns:
        ChromaDB-compatible where dictionary.
    """
    if filters is None:
        return None

    if isinstance(filters, Filter):
        # Single filter
        op_map = {
            FilterOperator.EQ: "$eq",
            FilterOperator.NE: "$ne",
            FilterOperator.GT: "$gt",
            FilterOperator.GTE: "$gte",
            FilterOperator.LT: "$lt",
            FilterOperator.LTE: "$lte",
            FilterOperator.IN: "$in",
            FilterOperator.NIN: "$nin",
            FilterOperator.CONTAINS: "$contains",
        }
        chroma_op = op_map.get(filters.operator, "$eq")

        if filters.operator == FilterOperator.EQ:
            # Simple equality can omit operator
            return {filters.field: filters.value}
        return {filters.field: {chroma_op: filters.value}}

    # FilterGroup - combine with $and/$or
    if not filters.filters:
        return None

    children = [_build_chroma_where(f) for f in filters.filters]
    children = [c for c in children if c is not None]

    if not children:
        return None
    if len(children) == 1:
        return children[0]

    chroma_op = "$and" if filters.operator == "and" else "$or"
    return {chroma_op: children}


class ChromaAdapter[T]:
    """ChromaDB implementation of VectorStore protocol.

    Stores typed data models (Pydantic or dataclass) with vector embeddings
    and supports hybrid search.

    Attributes:
        collection: The underlying ChromaDB collection.
        data_type: The type of data model being stored.
    """

    def __init__(self, collection: Collection, data_type: type[T]) -> None:
        """Initialize adapter with a ChromaDB collection.

        Use factory methods instead of direct construction.

        Args:
            collection: ChromaDB collection instance.
            data_type: Type of data model to store.
        """
        self._collection = collection
        self._data_type = data_type

    @classmethod
    def from_client(
        cls,
        client: chromadb.ClientAPI,  # type: ignore[name-defined]
        collection_name: str,
        data_type: type[T],
    ) -> ChromaAdapter[T]:
        """Create adapter from existing ChromaDB client.

        Args:
            client: ChromaDB client instance.
            collection_name: Name of collection to use/create.
            data_type: Type of data model to store.

        Returns:
            Configured ChromaAdapter instance.
        """
        collection = client.get_or_create_collection(name=collection_name)
        return cls(collection, data_type)

    @classmethod
    def from_path(
        cls,
        path: str,
        collection_name: str,
        data_type: type[T],
    ) -> ChromaAdapter[T]:
        """Create adapter with persistent storage.

        Args:
            path: Directory path for persistent storage.
            collection_name: Name of collection to use/create.
            data_type: Type of data model to store.

        Returns:
            Configured ChromaAdapter instance.
        """
        try:
            import chromadb
        except ImportError as e:
            raise ImportError(
                "chromadb is required for ChromaAdapter. Install with: pip install agentecs[chroma]"
            ) from e

        client = chromadb.PersistentClient(path=path)
        return cls.from_client(client, collection_name, data_type)

    @classmethod
    def from_memory(
        cls,
        collection_name: str,
        data_type: type[T],
    ) -> ChromaAdapter[T]:
        """Create adapter with ephemeral (in-memory) storage.

        Args:
            collection_name: Name of collection to use/create.
            data_type: Type of data model to store.

        Returns:
            Configured ChromaAdapter instance.
        """
        try:
            import chromadb
        except ImportError as e:
            raise ImportError(
                "chromadb is required for ChromaAdapter. Install with: pip install agentecs[chroma]"
            ) from e

        client = chromadb.EphemeralClient()
        return cls.from_client(client, collection_name, data_type)

    @property
    def collection(self) -> Collection:
        """Get the underlying ChromaDB collection."""
        return self._collection

    @property
    def data_type(self) -> type[T]:
        """Get the data type being stored."""
        return self._data_type

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
        metadata = _serialize_to_metadata(data, self._data_type)
        self._collection.add(
            ids=[id],
            embeddings=[embedding],  # type: ignore[arg-type]
            documents=[text],
            metadatas=[metadata],
        )
        return id

    def add_batch(self, items: list[VectorStoreItem[T]]) -> list[str]:
        """Add multiple items to the store.

        Args:
            items: List of items to add.

        Returns:
            List of IDs for added items.
        """
        if not items:
            return []

        ids = [item.id for item in items]
        embeddings = [item.embedding for item in items]
        documents = [item.text for item in items]
        metadatas = [_serialize_to_metadata(item.data, self._data_type) for item in items]

        self._collection.add(
            ids=ids,
            embeddings=embeddings,  # type: ignore[arg-type]
            documents=documents,
            metadatas=metadatas,  # type: ignore[arg-type]
        )
        return ids

    def get(self, id: str) -> T | None:
        """Get an item by ID.

        Args:
            id: Item identifier.

        Returns:
            The data model if found, None otherwise.
        """
        result = self._collection.get(ids=[id], include=["metadatas"])
        if not result["ids"]:
            return None

        metadata = result["metadatas"][0]  # type: ignore[index]
        return _deserialize_from_metadata(metadata, self._data_type)  # type: ignore[arg-type]

    def get_batch(self, ids: list[str]) -> list[T | None]:
        """Get multiple items by ID.

        Args:
            ids: List of item identifiers.

        Returns:
            List of data models (None for missing items).
        """
        if not ids:
            return []

        result = self._collection.get(ids=ids, include=["metadatas"])

        # Build lookup from returned results
        found: dict[str, dict[str, Any]] = {}
        for i, id_ in enumerate(result["ids"]):
            found[id_] = result["metadatas"][i]  # type: ignore[index,assignment]

        # Return in original order
        return [
            _deserialize_from_metadata(found[id_], self._data_type) if id_ in found else None
            for id_ in ids
        ]

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
        # Check if exists
        existing = self._collection.get(ids=[id])
        if not existing["ids"]:
            return False

        update_kwargs: dict[str, Any] = {"ids": [id]}

        if embedding is not None:
            update_kwargs["embeddings"] = [embedding]
        if text is not None:
            update_kwargs["documents"] = [text]
        if data is not None:
            update_kwargs["metadatas"] = [_serialize_to_metadata(data, self._data_type)]

        self._collection.update(**update_kwargs)
        return True

    def delete(self, id: str) -> bool:
        """Delete an item.

        Args:
            id: Item identifier.

        Returns:
            True if item existed and was deleted.
        """
        # Check if exists first
        existing = self._collection.get(ids=[id])
        if not existing["ids"]:
            return False

        self._collection.delete(ids=[id])
        return True

    def delete_batch(self, ids: list[str]) -> int:
        """Delete multiple items.

        Args:
            ids: List of item identifiers.

        Returns:
            Number of items deleted.
        """
        if not ids:
            return 0

        # Check which exist
        existing = self._collection.get(ids=ids)
        existing_ids = set(existing["ids"])

        if not existing_ids:
            return 0

        self._collection.delete(ids=list(existing_ids))
        return len(existing_ids)

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
        where = _build_chroma_where(filters)

        if mode == SearchMode.KEYWORD:
            if query_text is None:
                raise ValueError("query_text required for keyword search")
            # ChromaDB doesn't have pure keyword search, use where_document
            result = self._collection.query(
                query_texts=[query_text],
                n_results=limit,
                where=where,
                include=["metadatas", "distances", "documents"],
            )
        elif mode == SearchMode.VECTOR:
            if query_embedding is None:
                raise ValueError("query_embedding required for vector search")
            result = self._collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=limit,
                where=where,
                include=["metadatas", "distances", "documents"],
            )
        else:  # HYBRID
            if query_embedding is None:
                raise ValueError("query_embedding required for hybrid search")
            # ChromaDB hybrid: use embedding + optional text filter
            result = self._collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                query_texts=[query_text] if query_text else None,
                n_results=limit,
                where=where,
                include=["metadatas", "distances", "documents"],
            )

        # Convert results
        results: list[SearchResult[T]] = []
        if result["ids"] and result["ids"][0]:
            ids = result["ids"][0]
            metadatas = result["metadatas"][0] if result["metadatas"] else [{}] * len(ids)
            distances = result["distances"][0] if result["distances"] else [0.0] * len(ids)

            for i, id_ in enumerate(ids):
                data = _deserialize_from_metadata(metadatas[i], self._data_type)  # type: ignore[arg-type]
                distance = distances[i]
                # Convert distance to score (cosine: score = 1 - distance/2 for [-1,1] range)
                # ChromaDB uses squared L2 by default, but we assume cosine was set
                score = max(0.0, 1.0 - distance)

                results.append(
                    SearchResult(
                        id=id_,
                        data=data,
                        score=score,
                        distance=distance,
                    )
                )

        return results

    def count(self) -> int:
        """Get total number of items in the store.

        Returns:
            Item count.
        """
        return int(self._collection.count())

    # Async variants - ChromaDB is sync, so we wrap in executor

    async def add_async(
        self,
        id: str,
        embedding: list[float],
        text: str,
        data: T,
    ) -> str:
        """Add a single item to the store (async).

        Note: ChromaDB is synchronous, this runs in thread executor.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.add(id, embedding, text, data)
        )

    async def add_batch_async(self, items: list[VectorStoreItem[T]]) -> list[str]:
        """Add multiple items to the store (async).

        Note: ChromaDB is synchronous, this runs in thread executor.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, lambda: self.add_batch(items))

    async def get_async(self, id: str) -> T | None:
        """Get an item by ID (async).

        Note: ChromaDB is synchronous, this runs in thread executor.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, lambda: self.get(id))

    async def search_async(
        self,
        query_embedding: list[float] | None = None,
        query_text: str | None = None,
        mode: SearchMode = SearchMode.VECTOR,
        filters: Filter | FilterGroup | None = None,
        limit: int = 10,
    ) -> list[SearchResult[T]]:
        """Search the store (async).

        Note: ChromaDB is synchronous, this runs in thread executor.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.search(query_embedding, query_text, mode, filters, limit)
        )
