from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator, Iterator
from typing import Any, TypeVar

T = TypeVar("T")


class SyncRunner:
    """Thread-safe async runner for sync contexts. Singleton per process."""

    _instance: SyncRunner | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    @classmethod
    def get(cls) -> SyncRunner:
        """Get the singleton SyncRunner instance, creating it if necessary."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls()
                    inst._start()
                    cls._instance = inst
        return cls._instance

    def _start(self) -> None:
        """Start the background event loop thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            daemon=True,
            name="sync-runner-loop",
        )
        self._thread.start()

    def run(self, coro: Any) -> Any:
        """Run an async coroutine in the sync context, blocking until complete."""
        if self._loop is None:
            raise RuntimeError("Runner not initialized")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def iterate(self, async_iter: AsyncIterator[T]) -> Iterator[T]:
        """Convert async iterator to sync iterator."""
        while True:
            try:
                yield self.run(async_iter.__anext__())
            except StopAsyncIteration:
                break
