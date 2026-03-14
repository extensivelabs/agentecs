"""Tests for scheduler execution and result combination.

Critical Invariants:
- Parallel execution is deterministic (same result every run)
- Combinable folds and LWW behave correctly
- Dev mode systems run in isolation
- Concurrency limiting works
"""

from dataclasses import dataclass

import pytest

from agentecs import (
    SchedulerConfig,
    ScopedAccess,
    World,
    component,
    system,
)
from agentecs.scheduling import SequentialScheduler, SimpleScheduler


@component
@dataclass
class Counter:
    value: int


@component
@dataclass
class CombinableCounter:
    """Counter that sums values when combined."""

    value: int

    def __combine__(self, other: "CombinableCounter") -> "CombinableCounter":
        return CombinableCounter(self.value + other.value)


@component
@dataclass
class Position:
    x: int
    y: int


@component
@dataclass
class MarkerA:
    pass


@component
@dataclass
class MarkerB:
    pass


@pytest.fixture
def scheduler() -> SimpleScheduler:
    """Create a SimpleScheduler with default config."""
    return SimpleScheduler()


# Core execution tests


@pytest.mark.asyncio
async def test_parallel_execution_deterministic():
    """CRITICAL: Parallel execution produces deterministic results.

    Why: Determinism is required for reproducibility and debugging.
    With LastWriterWins, later system (by registration) overwrites.
    """
    results = []

    for _ in range(3):  # Run multiple times to verify determinism
        world = World(execution=SimpleScheduler())
        entity = world.spawn(Counter(0))

        @system(reads=(Counter,), writes=(Counter,))
        def add_one(access: ScopedAccess) -> None:
            for e, c in access(Counter):
                access[e, Counter] = Counter(c.value + 1)

        @system(reads=(Counter,), writes=(Counter,))
        def add_ten(access: ScopedAccess) -> None:
            for e, c in access(Counter):
                access[e, Counter] = Counter(c.value + 10)

        world.register_system(add_one)
        world.register_system(add_ten)
        await world.tick_async()

        results.append(world.get_copy(entity, Counter).value)  # type: ignore

    # All runs should produce same result
    assert all(r == results[0] for r in results), f"Non-deterministic results: {results}"
    # With LastWriterWins, add_ten (registered second) overwrites add_one
    # Both see Counter(0), add_one writes Counter(1), add_ten writes Counter(10)
    # Result: Counter(10) because add_ten registered later
    assert results[0] == 10


@pytest.mark.asyncio
async def test_sequential_scheduler_same_as_max_concurrent_1():
    """SequentialScheduler is equivalent to SimpleScheduler(max_concurrent=1).

    Why: Ensures alias works correctly.
    """
    for scheduler_factory in [
        SequentialScheduler,
        lambda: SimpleScheduler(config=SchedulerConfig(max_concurrent=1)),
    ]:
        world = World(execution=scheduler_factory())
        entity = world.spawn(Counter(0))

        @system(reads=(Counter,), writes=(Counter,))
        def increment(access: ScopedAccess) -> None:
            for e, c in access(Counter):
                access[e, Counter] = Counter(c.value + 1)

        world.register_system(increment)
        await world.tick_async()

        assert world.get_copy(entity, Counter).value == 1  # type: ignore


# Merge behavior tests


@pytest.mark.asyncio
async def test_last_writer_wins_merge():
    """LastWriterWins: later registered system overwrites earlier.

    Why: Default merge behavior must be predictable and simple.
    """
    world = World(execution=SimpleScheduler(config=SchedulerConfig()))
    entity = world.spawn(Counter(0))

    @system(reads=(Counter,), writes=(Counter,))
    def first_writer(access: ScopedAccess) -> None:
        for e, _ in access(Counter):
            access[e, Counter] = Counter(100)

    @system(reads=(Counter,), writes=(Counter,))
    def second_writer(access: ScopedAccess) -> None:
        for e, _ in access(Counter):
            access[e, Counter] = Counter(200)

    world.register_system(first_writer)
    world.register_system(second_writer)
    await world.tick_async()

    # Second writer wins (registered later)
    assert world.get_copy(entity, Counter).value == 200  # type: ignore


@pytest.mark.asyncio
async def test_combinable_folds_writes():
    """Combinable writes are folded with __combine__."""
    world = World(execution=SimpleScheduler())
    entity = world.spawn(CombinableCounter(0))

    @system(reads=(CombinableCounter,), writes=(CombinableCounter,))
    def add_five(access: ScopedAccess) -> None:
        for e, _ in access(CombinableCounter):
            access[e, CombinableCounter] = CombinableCounter(5)

    @system(reads=(CombinableCounter,), writes=(CombinableCounter,))
    def add_three(access: ScopedAccess) -> None:
        for e, _ in access(CombinableCounter):
            access[e, CombinableCounter] = CombinableCounter(3)

    world.register_system(add_five)
    world.register_system(add_three)
    await world.tick_async()

    assert world.get_copy(entity, CombinableCounter).value == 8  # type: ignore


@pytest.mark.asyncio
async def test_combinable_and_non_combinable_mixed():
    """Combinable folds while non-combinable still uses LWW."""
    world = World(execution=SimpleScheduler())
    entity = world.spawn(CombinableCounter(0), Position(0, 0))

    @system(reads=(CombinableCounter, Position), writes=(CombinableCounter, Position))
    def writer_one(access: ScopedAccess) -> None:
        for e, _, _ in access(CombinableCounter, Position):
            access[e, CombinableCounter] = CombinableCounter(2)
            access[e, Position] = Position(1, 1)

    @system(reads=(CombinableCounter, Position), writes=(CombinableCounter, Position))
    def writer_two(access: ScopedAccess) -> None:
        for e, _, _ in access(CombinableCounter, Position):
            access[e, CombinableCounter] = CombinableCounter(3)
            access[e, Position] = Position(9, 9)

    world.register_system(writer_one)
    world.register_system(writer_two)
    await world.tick_async()

    combined = world.get_copy(entity, CombinableCounter)
    position = world.get_copy(entity, Position)

    assert combined is not None
    assert position is not None
    assert combined.value == 5
    assert position == Position(9, 9)


@pytest.mark.asyncio
async def test_combinable_within_single_system():
    """Within one system, repeated writes still fold for Combinable types."""
    world = World(execution=SimpleScheduler())
    combinable_entity = world.spawn(CombinableCounter(0))
    plain_entity = world.spawn(Counter(0))

    @system(reads=(CombinableCounter, Counter), writes=(CombinableCounter, Counter))
    def writer(access: ScopedAccess) -> None:
        for e, _ in access(CombinableCounter):
            access[e, CombinableCounter] = CombinableCounter(4)
            access[e, CombinableCounter] = CombinableCounter(6)

        for e, _ in access(Counter):
            access[e, Counter] = Counter(4)
            access[e, Counter] = Counter(6)

    world.register_system(writer)
    await world.tick_async()

    combinable = world.get_copy(combinable_entity, CombinableCounter)
    plain = world.get_copy(plain_entity, Counter)

    assert combinable is not None
    assert plain is not None
    assert combinable.value == 10
    assert plain.value == 6


# Dev mode tests


@pytest.mark.asyncio
async def test_dev_mode_runs_in_isolation():
    """CRITICAL: Dev mode systems run in their own execution group.

    Why: Dev mode needs isolation for debugging without affecting others.
    """
    world = World(execution=SimpleScheduler())
    entity = world.spawn(Counter(0))
    execution_order = []

    @system.dev()
    def dev_system(access: ScopedAccess) -> None:
        execution_order.append("dev")
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 1)

    @system(reads=(Counter,), writes=(Counter,))
    def normal_system(access: ScopedAccess) -> None:
        execution_order.append("normal")
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 10)

    world.register_system(dev_system)
    world.register_system(normal_system)
    await world.tick_async()

    # Dev system runs first (in its own group), normal sees its result
    # Dev: 0 -> 1, Normal: 1 -> 11
    assert world.get_copy(entity, Counter).value == 11  # type: ignore


# Concurrency tests


@pytest.mark.asyncio
async def test_max_concurrent_limits_parallelism():
    """max_concurrent limits how many systems run concurrently.

    Why: Needed for rate limiting external API calls.
    """
    import asyncio

    concurrent_count = 0
    max_observed = 0

    world = World(execution=SimpleScheduler(config=SchedulerConfig(max_concurrent=2)))

    async def tracking_logic() -> None:
        nonlocal concurrent_count, max_observed
        concurrent_count += 1
        max_observed = max(max_observed, concurrent_count)
        await asyncio.sleep(0.01)  # Small delay to overlap
        concurrent_count -= 1

    # Create 5 async systems with unique names
    @system(reads=(), writes=())
    async def sys_0(access: ScopedAccess) -> None:
        await tracking_logic()

    @system(reads=(), writes=())
    async def sys_1(access: ScopedAccess) -> None:
        await tracking_logic()

    @system(reads=(), writes=())
    async def sys_2(access: ScopedAccess) -> None:
        await tracking_logic()

    @system(reads=(), writes=())
    async def sys_3(access: ScopedAccess) -> None:
        await tracking_logic()

    @system(reads=(), writes=())
    async def sys_4(access: ScopedAccess) -> None:
        await tracking_logic()

    world.register_system(sys_0)
    world.register_system(sys_1)
    world.register_system(sys_2)
    world.register_system(sys_3)
    world.register_system(sys_4)

    await world.tick_async()

    # Should never exceed max_concurrent=2
    assert max_observed <= 2


# Retry tests


@pytest.mark.asyncio
async def test_retry_policy_retries_on_failure():
    """Retry policy retries failed systems.

    Why: External APIs may have transient failures.
    """
    from agentecs.scheduling.models import RetryPolicy

    attempts = 0

    world = World(
        execution=SimpleScheduler(
            config=SchedulerConfig(retry_policy=RetryPolicy(max_attempts=3, on_exhausted="fail"))
        )
    )

    @system(reads=(), writes=())
    def flaky_system(access: ScopedAccess) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("Transient failure")

    world.register_system(flaky_system)
    await world.tick_async()

    # Should have retried and eventually succeeded
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_skip_on_exhausted():
    """on_exhausted='skip' continues without failed system's results.

    Why: Sometimes it's better to proceed than fail entirely.
    """
    from agentecs.scheduling.models import RetryPolicy

    world = World(
        execution=SimpleScheduler(
            config=SchedulerConfig(retry_policy=RetryPolicy(max_attempts=2, on_exhausted="skip"))
        )
    )
    entity = world.spawn(Counter(0))

    @system(reads=(), writes=())
    def always_fails(access: ScopedAccess) -> None:
        raise RuntimeError("Always fails")

    @system(reads=(Counter,), writes=(Counter,))
    def succeeds(access: ScopedAccess) -> None:
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 1)

    world.register_system(always_fails)
    world.register_system(succeeds)

    # Should not raise, should apply succeeds' result
    await world.tick_async()
    assert world.get_copy(entity, Counter).value == 1  # type: ignore


# Error handling tests


@pytest.mark.asyncio
async def test_system_exception_propagates():
    """System exceptions propagate directly (no wrapping without retry).

    Why: Clear error messages for debugging.
    """
    world = World(execution=SimpleScheduler())

    @system(reads=(), writes=())
    def failing_system(access: ScopedAccess) -> None:
        raise ValueError("System failed!")

    world.register_system(failing_system)

    # Without retry, original exception propagates directly
    with pytest.raises(ValueError, match="System failed!"):
        await world.tick_async()


# ExecutionGroupBuilder test


@pytest.mark.asyncio
async def test_custom_execution_group_builder():
    """Custom ExecutionGroupBuilder can control grouping strategy.

    Why: Extension point for future scheduling strategies (dependencies, frequency).
    """
    from agentecs.core.system import SystemDescriptor
    from agentecs.scheduling.models import ExecutionGroup, ExecutionPlan

    # Custom builder that puts each system in its own group (all sequential)
    class SequentialGroupBuilder:
        def build(self, systems: list[SystemDescriptor]) -> ExecutionPlan:
            return [ExecutionGroup(systems=[s]) for s in systems]

    world = World(execution=SimpleScheduler(group_builder=SequentialGroupBuilder()))
    entity = world.spawn(Counter(0))
    execution_order: list[str] = []

    @system(reads=(Counter,), writes=(Counter,))
    def first(access: ScopedAccess) -> None:
        execution_order.append("first")
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 1)

    @system(reads=(Counter,), writes=(Counter,))
    def second(access: ScopedAccess) -> None:
        execution_order.append("second")
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 10)

    world.register_system(first)
    world.register_system(second)

    # Verify each system is in its own group
    plan = world._execution.get_execution_plan_info()
    assert len(plan) == 2  # Two groups
    assert len(plan[0]) == 1  # One system each
    assert len(plan[1]) == 1

    await world.tick_async()

    # With sequential groups, second sees first's result: 0 -> 1 -> 11
    assert world.get_copy(entity, Counter).value == 11  # type: ignore


# Optional access declarations test


@pytest.mark.asyncio
async def test_optional_access_declarations():
    """Systems without access declarations have full access but run in parallel.

    Why: Simplifies getting started, no boilerplate for simple systems.
    """
    world = World(execution=SimpleScheduler())
    entity = world.spawn(Counter(0))

    @system()  # No reads/writes declared = full access
    def full_access_system(access: ScopedAccess) -> None:
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 1)

    @system()  # Another full access system
    def another_full_access(access: ScopedAccess) -> None:
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 10)

    world.register_system(full_access_system)
    world.register_system(another_full_access)

    # Both run in parallel (not like dev mode which runs alone)
    scheduler = world._execution
    plan = scheduler.get_execution_plan_info()

    # Should be one group with both systems (not separate dev groups)
    assert len(plan) == 1
    assert len(plan[0]) == 2

    await world.tick_async()

    # LastWriterWins: another_full_access (registered second) wins
    assert world.get_copy(entity, Counter).value == 10  # type: ignore


# Multiple ticks test


@pytest.mark.asyncio
async def test_multiple_ticks_accumulate():
    """Multiple ticks accumulate changes correctly.

    Why: Basic tick semantics must work over time.
    """
    world = World(execution=SimpleScheduler())
    entity = world.spawn(Counter(0))

    @system(reads=(Counter,), writes=(Counter,))
    def increment(access: ScopedAccess) -> None:
        for e, c in access(Counter):
            access[e, Counter] = Counter(c.value + 1)

    world.register_system(increment)

    for _ in range(10):
        await world.tick_async()

    assert world.get_copy(entity, Counter).value == 10  # type: ignore
