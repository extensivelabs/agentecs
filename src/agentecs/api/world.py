"""World with the framework's default storage and execution strategy."""

from __future__ import annotations

from agentecs.protocols.execution import ExecutionStrategy
from agentecs.protocols.storage import Storage
from agentecs.services.scheduler import SimpleScheduler
from agentecs.services.storage import LocalStorage
from agentecs.services.world import World as _World


class World(_World):
    """World defaulting to in-memory storage and the parallel scheduler."""

    def __init__(
        self,
        storage: Storage | None = None,
        execution: ExecutionStrategy | None = None,
    ) -> None:
        super().__init__(storage or LocalStorage(), execution or SimpleScheduler())
