"""Data models for tracing infrastructure.

These models are designed to be storage-agnostic and work with any
snapshot format that can be serialized to JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TickRecord:
    """Complete record of a single tick for history storage.

    This is the unit of storage for the HistoryStore. It captures everything
    needed to reconstruct or replay the world state at a given tick.

    Attributes:
        tick: The tick number.
        timestamp: Unix timestamp when the tick occurred.
        snapshot: Complete world state snapshot (JSON-serializable dict).
        events: List of events that occurred during this tick.
        system_timings: Optional dict of system_name -> execution_time_ms.
        metadata: Optional arbitrary metadata for annotations.

    Example:
        record = TickRecord(
            tick=42,
            timestamp=1704067200.0,
            snapshot={"tick": 42, "entities": [...]},
            events=[{"type": "spawn", "entity_id": 5}],
            system_timings={"physics": 12.5, "ai": 45.2},
        )
    """

    tick: int
    timestamp: float
    snapshot: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    system_timings: dict[str, float] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        result: dict[str, Any] = {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "snapshot": self.snapshot,
            "events": self.events,
        }
        if self.system_timings is not None:
            result["system_timings"] = self.system_timings
        if self.metadata is not None:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TickRecord:
        """Create from dictionary (for deserialization)."""
        return cls(
            tick=data["tick"],
            timestamp=data["timestamp"],
            snapshot=data["snapshot"],
            events=data.get("events", []),
            system_timings=data.get("system_timings"),
            metadata=data.get("metadata"),
        )
