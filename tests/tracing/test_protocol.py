"""Tests for HistoryStore protocol.

Why these tests exist:
- HistoryStore is the core protocol for history storage
- Protocol compliance must be verifiable
- Basic operations must work correctly
"""

from agentecs.tracing import HistoryStore, TickRecord


class SimpleHistoryStore:
    """Minimal HistoryStore implementation for testing."""

    def __init__(self, max_ticks: int = 100) -> None:
        self._records: dict[int, TickRecord] = {}
        self._max_ticks = max_ticks

    def record_tick(self, record: TickRecord) -> None:
        self._records[record.tick] = record
        # Evict oldest if over limit
        if len(self._records) > self._max_ticks:
            oldest = min(self._records.keys())
            del self._records[oldest]

    def get_tick(self, tick: int) -> TickRecord | None:
        return self._records.get(tick)

    def get_snapshot(self, tick: int) -> dict | None:
        record = self._records.get(tick)
        return record.snapshot if record else None

    def get_events(self, start_tick: int, end_tick: int) -> list[dict]:
        events = []
        for tick in range(start_tick, end_tick + 1):
            record = self._records.get(tick)
            if record:
                events.extend(record.events)
        return events

    def get_tick_range(self) -> tuple[int, int] | None:
        if not self._records:
            return None
        return min(self._records.keys()), max(self._records.keys())

    def clear(self) -> None:
        self._records.clear()

    @property
    def tick_count(self) -> int:
        return len(self._records)


def test_simple_store_is_history_store() -> None:
    """SimpleHistoryStore implements HistoryStore protocol."""
    store = SimpleHistoryStore()
    assert isinstance(store, HistoryStore)


def test_record_and_retrieve_tick() -> None:
    """Can record and retrieve a tick."""
    store = SimpleHistoryStore()
    record = TickRecord(
        tick=1,
        timestamp=100.0,
        snapshot={"tick": 1, "entities": []},
    )
    store.record_tick(record)

    retrieved = store.get_tick(1)
    assert retrieved is not None
    assert retrieved.tick == 1
    assert retrieved.snapshot == {"tick": 1, "entities": []}


def test_get_snapshot() -> None:
    """get_snapshot returns just the snapshot dict."""
    store = SimpleHistoryStore()
    store.record_tick(
        TickRecord(
            tick=5,
            timestamp=500.0,
            snapshot={"data": "test"},
            events=[{"type": "event"}],
        )
    )

    snapshot = store.get_snapshot(5)
    assert snapshot == {"data": "test"}


def test_get_snapshot_missing() -> None:
    """get_snapshot returns None for missing tick."""
    store = SimpleHistoryStore()
    assert store.get_snapshot(999) is None


def test_get_events_range() -> None:
    """get_events collects events from tick range."""
    store = SimpleHistoryStore()
    store.record_tick(TickRecord(tick=1, timestamp=0, snapshot={}, events=[{"a": 1}]))
    store.record_tick(TickRecord(tick=2, timestamp=0, snapshot={}, events=[{"b": 2}]))
    store.record_tick(TickRecord(tick=3, timestamp=0, snapshot={}, events=[{"c": 3}]))

    events = store.get_events(1, 2)
    assert len(events) == 2
    assert {"a": 1} in events
    assert {"b": 2} in events
    assert {"c": 3} not in events


def test_get_tick_range_empty() -> None:
    """get_tick_range returns None when empty."""
    store = SimpleHistoryStore()
    assert store.get_tick_range() is None


def test_get_tick_range() -> None:
    """get_tick_range returns min/max ticks."""
    store = SimpleHistoryStore()
    store.record_tick(TickRecord(tick=10, timestamp=0, snapshot={}))
    store.record_tick(TickRecord(tick=20, timestamp=0, snapshot={}))
    store.record_tick(TickRecord(tick=15, timestamp=0, snapshot={}))

    tick_range = store.get_tick_range()
    assert tick_range == (10, 20)


def test_clear() -> None:
    """Clear removes all history."""
    store = SimpleHistoryStore()
    store.record_tick(TickRecord(tick=1, timestamp=0, snapshot={}))
    store.record_tick(TickRecord(tick=2, timestamp=0, snapshot={}))
    assert store.tick_count == 2

    store.clear()
    assert store.tick_count == 0
    assert store.get_tick_range() is None


def test_bounded_storage() -> None:
    """Store evicts oldest ticks when limit exceeded.

    Why: In-memory stores need bounded storage to prevent memory exhaustion.
    """
    store = SimpleHistoryStore(max_ticks=3)

    # Add 4 ticks
    for i in range(4):
        store.record_tick(TickRecord(tick=i, timestamp=float(i), snapshot={"i": i}))

    # Should only have 3 ticks, oldest evicted
    assert store.tick_count == 3
    assert store.get_tick(0) is None  # Evicted
    assert store.get_tick(1) is not None
    assert store.get_tick(2) is not None
    assert store.get_tick(3) is not None
