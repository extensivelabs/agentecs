"""Tests for tracing data models.

Why these tests exist:
- TickRecord is the core data structure for history storage
- Serialization round-trip must preserve all data correctly
- Optional fields must be handled properly
"""

import pytest

from agentecs.tracing import TickRecord


@pytest.mark.parametrize(
    ("kwargs", "expected_events", "has_timings", "has_metadata"),
    [
        (
            {"tick": 42, "timestamp": 1704067200.0, "snapshot": {"tick": 42, "entities": []}},
            [],
            False,
            False,
        ),
        (
            {
                "tick": 100,
                "timestamp": 1704067300.0,
                "snapshot": {"tick": 100, "entity_count": 5},
                "events": [{"type": "spawn", "entity_id": 1}],
                "system_timings": {"physics": 12.5, "ai": 45.2},
                "metadata": {"description": "test run"},
            },
            [{"type": "spawn", "entity_id": 1}],
            True,
            True,
        ),
    ],
    ids=["minimal", "full"],
)
def test_tick_record_creation(kwargs, expected_events, has_timings, has_metadata) -> None:
    """TickRecord handles required and optional fields correctly."""
    record = TickRecord(**kwargs)
    assert record.tick == kwargs["tick"]
    assert record.timestamp == kwargs["timestamp"]
    assert record.snapshot == kwargs["snapshot"]
    assert record.events == expected_events
    assert (record.system_timings is not None) == has_timings
    assert (record.metadata is not None) == has_metadata


@pytest.mark.parametrize(
    ("kwargs", "check_missing", "check_present"),
    [
        (
            {"tick": 1, "timestamp": 0.0, "snapshot": {}},
            ["system_timings", "metadata"],
            {"tick": 1, "timestamp": 0.0, "snapshot": {}, "events": []},
        ),
        (
            {
                "tick": 5,
                "timestamp": 123.456,
                "snapshot": {"test": True},
                "events": [{"a": 1}],
                "system_timings": {"sys1": 10.0},
                "metadata": {"key": "value"},
            },
            [],
            {
                "tick": 5,
                "snapshot": {"test": True},
                "system_timings": {"sys1": 10.0},
                "metadata": {"key": "value"},
            },
        ),
    ],
    ids=["minimal", "full"],
)
def test_tick_record_to_dict(kwargs, check_missing, check_present) -> None:
    """to_dict handles optional fields correctly."""
    record = TickRecord(**kwargs)
    data = record.to_dict()

    for key in check_missing:
        assert key not in data

    for key, value in check_present.items():
        assert data[key] == value


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
