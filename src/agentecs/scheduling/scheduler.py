"""System scheduler with configurable parallelism and merge strategies.

Usage:
    # Default scheduler (all systems parallel, dev systems isolated)
    scheduler = SimpleScheduler()
    scheduler.register_system(movement_system)
    await scheduler.tick_async(world)

    # Custom execution group builder (future: dependencies, frequency, etc.)
    from agentecs.scheduling import SingleGroupBuilder
    scheduler = SimpleScheduler(group_builder=SingleGroupBuilder())

    # Retry configuration (requires tenacity: pip install agentecs[retry])
    from agentecs.scheduling import RetryPolicy, SchedulerConfig
    config = SchedulerConfig(retry_policy=RetryPolicy(max_attempts=3, backoff="exponential"))
    scheduler = SimpleScheduler(config=config)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from agentecs.core.system import SystemDescriptor
from agentecs.scheduling.merge_strategies import (
    merge_error_on_conflict,
    merge_last_writer_wins,
    merge_mergeable_first,
)
from agentecs.scheduling.models import (
    ExecutionGroup,
    ExecutionGroupBuilder,
    ExecutionPlan,
    MergeStrategy,
    RetryPolicy,
    SchedulerConfig,
    SingleGroupBuilder,
)
from agentecs.world.result import SystemResult

# Optional tenacity import for retry functionality
try:
    import tenacity

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

if TYPE_CHECKING:
    from agentecs.world.world import World


class ExecutionBackend(Protocol):
    """Protocol for pluggable execution backends.

    Default uses asyncio.gather(). Future backends can implement
    this protocol for distributed execution across nodes.
    """

    async def execute_group(
        self, systems: list[SystemDescriptor], world: World
    ) -> list[SystemResult]:
        """Execute a group of systems concurrently and return their results."""
        ...


class SimpleScheduler:
    """Scheduler with parallel execution and configurable merge strategy.

    All systems execute in parallel (snapshot isolation), results merged
    at tick boundary using configured strategy.

    Execution grouping is delegated to an ExecutionGroupBuilder, enabling
    future extensions for dependency-based, frequency-based, or custom
    grouping strategies.

    Args:
        config: Scheduler configuration (merge strategy, concurrency, retry).
        group_builder: Strategy for building execution groups from systems.
            Defaults to SingleGroupBuilder (all parallel, dev systems isolated).
    """

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        group_builder: ExecutionGroupBuilder | None = None,
    ) -> None:
        self._config = config or SchedulerConfig()
        self._group_builder = group_builder or SingleGroupBuilder()
        self._systems: list[SystemDescriptor] = []
        self._execution_plan: ExecutionPlan | None = None

    def register_system(self, descriptor: SystemDescriptor) -> None:
        """Register system for execution. Invalidates cached execution plan."""
        self._systems.append(descriptor)
        self._execution_plan = None

    def build_execution_plan(self) -> ExecutionPlan:
        """Build execution plan using the configured group builder."""
        return self._group_builder.build(self._systems)

    async def tick_async(self, world: World) -> None:
        """Execute all systems once, parallelizing where possible."""
        if self._execution_plan is None:
            self._execution_plan = self.build_execution_plan()

        for group in self._execution_plan:
            await self._execute_group_async(world, group)

    async def _execute_group_async(self, world: World, group: ExecutionGroup) -> None:
        """Execute a group of systems in parallel, merge and apply results."""
        if not group.systems:
            return

        # Execute systems with concurrency limiting
        results = await self._execute_systems_async(world, group.systems)

        # Merge results using configured strategy
        system_names = [s.name for s in group.systems]
        merged = self._merge_results(results, system_names)

        # Apply merged results
        await world.apply_result_async(merged)

    async def _execute_systems_async(
        self, world: World, systems: list[SystemDescriptor]
    ) -> list[SystemResult]:
        """Execute systems with optional concurrency limiting and retry."""
        max_concurrent = self._config.max_concurrent

        if max_concurrent is None:
            # Unlimited concurrency
            tasks = [self._execute_with_retry(world, system) for system in systems]
            return list(await asyncio.gather(*tasks))
        else:
            # Semaphore-limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_execute(system: SystemDescriptor) -> SystemResult:
                async with semaphore:
                    return await self._execute_with_retry(world, system)

            tasks = [limited_execute(system) for system in systems]
            return list(await asyncio.gather(*tasks))

    async def _execute_with_retry(self, world: World, system: SystemDescriptor) -> SystemResult:
        """Execute system with retry policy.

        Uses tenacity for retry logic when max_attempts > 1.
        Requires tenacity to be installed: pip install agentecs[retry]
        """
        policy = self._config.retry_policy

        if policy.max_attempts <= 1:
            return await world.execute_system_async(system)

        if not TENACITY_AVAILABLE:
            msg = "Retry policy requires tenacity. Install with: pip install agentecs[retry]"
            raise ImportError(msg)

        retryer = self._build_retryer(policy)

        try:
            async for attempt in retryer:
                with attempt:
                    return await world.execute_system_async(system)
        except tenacity.RetryError as e:
            if policy.on_exhausted == "skip":
                return SystemResult()  # Empty result, skip this system
            msg = f"{system.name} failed after {policy.max_attempts} attempts"
            raise RuntimeError(msg) from e.last_attempt.exception()

        return SystemResult()  # pragma: no cover

    def _build_retryer(self, policy: RetryPolicy) -> tenacity.AsyncRetrying:
        """Build a tenacity retryer from RetryPolicy configuration."""
        stop = tenacity.stop_after_attempt(policy.max_attempts)

        wait: tenacity.wait.wait_base
        if policy.backoff == "exponential":
            wait = tenacity.wait_exponential(multiplier=policy.base_delay, min=policy.base_delay)
        elif policy.backoff == "linear":
            wait = tenacity.wait_incrementing(start=policy.base_delay, increment=policy.base_delay)
        else:
            wait = tenacity.wait_none()

        return tenacity.AsyncRetrying(
            stop=stop,
            wait=wait,
            reraise=False,
        )

    def _merge_results(self, results: list[SystemResult], system_names: list[str]) -> SystemResult:
        """Merge results using configured strategy."""
        strategy = self._config.merge_strategy

        if strategy == MergeStrategy.LAST_WRITER_WINS:
            return merge_last_writer_wins(results, system_names)
        elif strategy == MergeStrategy.MERGEABLE_FIRST:
            return merge_mergeable_first(results, system_names)
        elif strategy == MergeStrategy.ERROR:
            return merge_error_on_conflict(results, system_names)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

    def tick(self, world: World) -> None:
        """Synchronous wrapper for tick_async."""
        asyncio.run(self.tick_async(world))

    def get_execution_plan_info(self) -> list[list[str]]:
        """Get human-readable execution plan (for debugging)."""
        if self._execution_plan is None:
            self._execution_plan = self.build_execution_plan()

        return [[s.name for s in group.systems] for group in self._execution_plan]


# Alias for sequential execution (max_concurrent=1)
def SequentialScheduler() -> SimpleScheduler:  # noqa: N802
    """Create a scheduler that executes systems one at a time.

    Equivalent to SimpleScheduler with max_concurrent=1.
    Useful for debugging or when parallelism isn't needed.
    """
    return SimpleScheduler(config=SchedulerConfig(max_concurrent=1))
