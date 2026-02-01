"""Tests for tracing data models.

Why these tests exist:
- TickRecord is the core data structure for history storage
- Serialization round-trip must preserve all data correctly
- Optional fields must be handled properly
"""

from agentecs.tracing import TickRecord


def test_tick_record_creation() -> None:
    """TickRecord can be created with required fields."""
    record = TickRecord(
        tick=42,
        timestamp=1704067200.0,
        snapshot={"tick": 42, "entities": []},
    )
    assert record.tick == 42
    assert record.timestamp == 1704067200.0
    assert record.snapshot == {"tick": 42, "entities": []}
    assert record.events == []
    assert record.system_timings is None
    assert record.metadata is None


def test_tick_record_with_all_fields() -> None:
    """TickRecord can include optional fields."""
    record = TickRecord(
        tick=100,
        timestamp=1704067300.0,
        snapshot={"tick": 100, "entity_count": 5},
        events=[{"type": "spawn", "entity_id": 1}],
        system_timings={"physics": 12.5, "ai": 45.2},
        metadata={"description": "test run"},
    )
    assert record.tick == 100
    assert len(record.events) == 1
    assert record.system_timings["physics"] == 12.5
    assert record.metadata["description"] == "test run"


def test_tick_record_to_dict_minimal() -> None:
    """to_dict excludes None optional fields."""
    record = TickRecord(
        tick=1,
        timestamp=0.0,
        snapshot={},
    )
    data = record.to_dict()
    assert data == {
        "tick": 1,
        "timestamp": 0.0,
        "snapshot": {},
        "events": [],
    }
    assert "system_timings" not in data
    assert "metadata" not in data


def test_tick_record_to_dict_full() -> None:
    """to_dict includes all fields when present."""
    record = TickRecord(
        tick=5,
        timestamp=123.456,
        snapshot={"test": True},
        events=[{"a": 1}],
        system_timings={"sys1": 10.0},
        metadata={"key": "value"},
    )
    data = record.to_dict()
    assert data["tick"] == 5
    assert data["snapshot"] == {"test": True}
    assert data["system_timings"] == {"sys1": 10.0}
    assert data["metadata"] == {"key": "value"}


def test_tick_record_round_trip() -> None:
    """TickRecord survives serialization round-trip.

    Why: History storage requires reliable serialization/deserialization.
    """
    original = TickRecord(
        tick=42,
        timestamp=1704067200.123,
        snapshot={"tick": 42, "entities": [{"id": 1, "components": []}]},
        events=[{"type": "spawn", "id": 1}, {"type": "change", "id": 1}],
        system_timings={"system_a": 15.5, "system_b": 30.2},
        metadata={"run_id": "abc123", "notes": "test"},
    )

    # Serialize and deserialize
    data = original.to_dict()
    restored = TickRecord.from_dict(data)

    assert restored.tick == original.tick
    assert restored.timestamp == original.timestamp
    assert restored.snapshot == original.snapshot
    assert restored.events == original.events
    assert restored.system_timings == original.system_timings
    assert restored.metadata == original.metadata


def test_tick_record_from_dict_minimal() -> None:
    """from_dict handles missing optional fields."""
    data = {
        "tick": 10,
        "timestamp": 500.0,
        "snapshot": {"x": 1},
    }
    record = TickRecord.from_dict(data)
    assert record.tick == 10
    assert record.events == []
    assert record.system_timings is None
    assert record.metadata is None
