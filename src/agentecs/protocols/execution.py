"""Protocols for system execution and execution planning."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from agentecs.models.identity import EntityId
from agentecs.models.result import SystemResult
from agentecs.models.scheduling import ExecutionPlan
from agentecs.models.system import SystemDescriptor


@runtime_checkable
class SystemExecutor(Protocol):
    """The slice of World an execution strategy is allowed to use."""

    async def execute_system_async(self, descriptor: SystemDescriptor) -> SystemResult:
        """Run one system and return the changes it recorded."""
        ...

    async def apply_result_async(self, result: SystemResult) -> list[EntityId]:
        """Apply recorded changes, returning the entities spawned."""
        ...


@runtime_checkable
class ExecutionStrategy(Protocol):
    """Protocol for pluggable system execution strategies.

    Enables different execution strategies:
    - Sequential: Simple one-by-one execution
    - Parallel: Conflict detection and parallel execution
    - Distributed: Cross-node execution
    - Learnable: Context-aware optimization

    The strategy is injected into World and handles all system registration
    and execution logic.
    """

    def register_system(self, descriptor: SystemDescriptor) -> None:
        """Register a system for execution.

        Args:
            descriptor: System metadata to register
        """
        ...

    async def tick_async(self, world: SystemExecutor) -> None:
        """Execute all registered systems once.

        Args:
            world: Executor providing execute_system_async() and apply_result_async()
        """
        ...


ExecutionGroupBuilder = Callable[[list[SystemDescriptor]], ExecutionPlan]
"""Builds execution plans from registered systems.

Extension point for scheduling strategies. Implementations determine how
systems are grouped for execution. Groups execute sequentially; systems
within groups execute in parallel.

Built-in implementations:
- build_single_group_plan: All systems in one group (default)

Future implementations (not yet built):
- DependencyGroupBuilder: Groups based on depends_on declarations
- FrequencyGroupBuilder: Groups based on tick frequency
- ConditionGroupBuilder: Groups based on runtime conditions
"""
