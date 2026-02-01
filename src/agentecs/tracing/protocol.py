"""Protocols for tracing infrastructure.

These protocols define the interface for history storage backends,
allowing different implementations (in-memory, file, database).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from agentecs.tracing.models import TickRecord


@runtime_checkable
class HistoryStore(Protocol):
    """Protocol for storing and retrieving tick history.

    Implementations store TickRecords and provide random access to
    past world states. This enables replay, debugging, and analysis.

    Example implementations:
        - InMemoryHistoryStore: Bounded buffer in memory (development)
        - FileHistoryStore: JSON/msgpack file storage (persistence)
        - SQLiteHistoryStore: Database storage (queryable)

    Usage:
        store = InMemoryHistoryStore(max_ticks=1000)

        # Record ticks as they happen
        store.record_tick(tick_record)

        # Later, retrieve for replay
        snapshot = store.get_snapshot(tick=42)
        events = store.get_events(start_tick=40, end_tick=50)

    Thread Safety:
        Implementations should be thread-safe for concurrent access.
    """

    def record_tick(self, record: TickRecord) -> None:
        """Record a tick's state and events.

        Args:
            record: Complete record of the tick to store.

        Note:
            Implementations may have bounded storage (e.g., last N ticks).
            Older records may be evicted when the limit is reached.
        """
        ...

    def get_tick(self, tick: int) -> TickRecord | None:
        """Get complete tick record.

        Args:
            tick: The tick number to retrieve.

        Returns:
            The TickRecord if available, None if not in storage.
        """
        ...

    def get_snapshot(self, tick: int) -> dict[str, Any] | None:
        """Get world snapshot at specific tick.

        Args:
            tick: The tick number to retrieve.

        Returns:
            The snapshot dict if available, None if tick not in storage.

        Note:
            This is a convenience method that extracts just the snapshot
            from the full TickRecord.
        """
        ...

    def get_events(self, start_tick: int, end_tick: int) -> list[dict[str, Any]]:
        """Get events in tick range (inclusive).

        Args:
            start_tick: First tick to include.
            end_tick: Last tick to include.

        Returns:
            Flattened list of all events in the range.
        """
        ...

    def get_tick_range(self) -> tuple[int, int] | None:
        """Get available tick range.

        Returns:
            Tuple of (min_tick, max_tick) if history exists, None if empty.
        """
        ...

    def clear(self) -> None:
        """Clear all stored history."""
        ...

    @property
    def tick_count(self) -> int:
        """Number of ticks currently stored."""
        ...
