"""Tracing infrastructure for recording and replaying world execution.

This module provides protocols and data structures for capturing tick history,
enabling debugging, analysis, and replay of world executions.

Usage:
    from agentecs.tracing import HistoryStore, TickRecord

    # Implement HistoryStore for your storage backend
    class MyHistoryStore:
        def record_tick(self, record: TickRecord) -> None:
            ...

    # Or use implementations from agentecs_viz:
    # from agentecs_viz.history import InMemoryHistoryStore
"""

from agentecs.tracing.models import TickRecord
from agentecs.tracing.protocol import HistoryStore

__all__ = [
    "HistoryStore",
    "TickRecord",
]
