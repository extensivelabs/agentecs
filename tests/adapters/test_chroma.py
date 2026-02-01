"""Tests for ChromaAdapter.

Focus: Serialization round-trip (complex), filter building (error-prone),
search mode validation (user-facing errors).
"""

import importlib.util
from dataclasses import dataclass

import pytest

from agentecs.adapters.chroma import (
    _build_chroma_where,
    _deserialize_from_metadata,
    _serialize_to_metadata,
)
from agentecs.adapters.models import Filter, FilterGroup, FilterOperator


@dataclass
class SimpleDoc:
    title: str
    count: int


@dataclass
class ComplexDoc:
    name: str
    tags: list[str]
    metadata: dict[str, int]
    optional: str | None = None


def test_serialize_roundtrip_simple_dataclass():
    """Simple dataclass survives serialization round-trip.

    Why: This is the core guarantee of the adapter - data integrity.
    """
    original = SimpleDoc(title="Test", count=42)
    metadata = _serialize_to_metadata(original, SimpleDoc)
    restored = _deserialize_from_metadata(metadata, SimpleDoc)

    assert restored.title == original.title
    assert restored.count == original.count


def test_serialize_roundtrip_complex_nested_types():
    """Complex nested types (lists, dicts) survive round-trip.

    Why: Nested structures require JSON serialization - easy to break.
    """
    original = ComplexDoc(
        name="Test",
        tags=["a", "b", "c"],
        metadata={"x": 1, "y": 2},
        optional=None,
    )
    metadata = _serialize_to_metadata(original, ComplexDoc)
    restored = _deserialize_from_metadata(metadata, ComplexDoc)

    assert restored.name == original.name
    assert restored.tags == original.tags
    assert restored.metadata == original.metadata
    assert restored.optional is None


def test_serialize_handles_none_values():
    """None values are preserved through serialization.

    Why: ChromaDB doesn't support None in metadata - we use sentinel keys.
    """
    original = ComplexDoc(name="Test", tags=[], metadata={}, optional=None)
    metadata = _serialize_to_metadata(original, ComplexDoc)

    # None should be stored as sentinel, not literally
    assert "optional" not in metadata or metadata.get("optional") is not None
    assert "_null_optional" in metadata

    restored = _deserialize_from_metadata(metadata, ComplexDoc)
    assert restored.optional is None


def test_filter_single_equality():
    """Single equality filter produces correct ChromaDB format."""
    f = Filter(field="status", operator=FilterOperator.EQ, value="active")
    result = _build_chroma_where(f)

    assert result == {"status": "active"}


def test_filter_with_operator():
    """Non-equality operators use ChromaDB operator syntax."""
    f = Filter(field="count", operator=FilterOperator.GT, value=10)
    result = _build_chroma_where(f)

    assert result == {"count": {"$gt": 10}}


def test_filter_group_and():
    """AND group combines filters correctly."""
    group = FilterGroup(
        operator="and",
        filters=[
            Filter(field="status", operator=FilterOperator.EQ, value="active"),
            Filter(field="count", operator=FilterOperator.GT, value=0),
        ],
    )
    result = _build_chroma_where(group)

    assert result == {"$and": [{"status": "active"}, {"count": {"$gt": 0}}]}


def test_filter_group_single_child_unwraps():
    """Single-child group unwraps to avoid unnecessary nesting.

    Why: ChromaDB may reject or mishandle unnecessary $and wrappers.
    """
    group = FilterGroup(
        operator="and",
        filters=[Filter(field="status", operator=FilterOperator.EQ, value="active")],
    )
    result = _build_chroma_where(group)

    # Should unwrap single child
    assert result == {"status": "active"}


def test_filter_none_returns_none():
    """None filter returns None (no filtering)."""
    assert _build_chroma_where(None) is None


# Integration test with real ChromaDB (optional dependency)
HAS_CHROMADB = importlib.util.find_spec("chromadb") is not None


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb not installed")
def test_chroma_add_get_roundtrip():
    """Full add/get cycle preserves data through ChromaDB.

    Why: Tests actual ChromaDB interaction, not just our serialization.
    """
    from agentecs.adapters.chroma import ChromaAdapter

    store = ChromaAdapter.from_memory("test_collection", SimpleDoc)

    doc = SimpleDoc(title="Hello", count=99)
    store.add("doc1", embedding=[0.1, 0.2, 0.3], text="hello world", data=doc)

    retrieved = store.get("doc1")

    assert retrieved is not None
    assert retrieved.title == "Hello"
    assert retrieved.count == 99


@pytest.mark.skipif(not HAS_CHROMADB, reason="chromadb not installed")
def test_chroma_search_requires_embedding_for_vector_mode():
    """Vector search without embedding raises clear error.

    Why: User-facing error messages should be helpful.
    """
    from agentecs.adapters.chroma import ChromaAdapter
    from agentecs.adapters.models import SearchMode

    store = ChromaAdapter.from_memory("test_search", SimpleDoc)

    with pytest.raises(ValueError, match="query_embedding required"):
        store.search(query_embedding=None, mode=SearchMode.VECTOR)
