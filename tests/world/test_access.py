"""Tests for access control and snapshot isolation.

Critical Invariants:
- Systems see their own writes (snapshot isolation)
- Systems don't see other systems' writes until tick boundary
- Access control is enforced (except dev mode)
"""

from dataclasses import dataclass

import pytest

from agentecs import ScopedAccess, World, component, system
from agentecs.world import AccessViolationError


@component
@dataclass
class TestValue:
    value: int


@component
@dataclass
class OtherValue:
    value: int


@pytest.fixture
def world():
    """Create a World for testing."""
    return World()


# Snapshot isolation tests - critical correctness mechanism


def test_system_sees_own_writes_immediately(world):
    """CRITICAL: System immediately sees its own writes in all contexts.

    Why: Snapshot isolation must maintain consistency within a system's execution.
    Tests: Direct read after write, multiple sequential writes, query results,
           and write-then-query scenarios.
    """
    entity = world.spawn(TestValue(10))

    seen_values = []

    @system(reads=(TestValue,), writes=(TestValue,))
    def test_all_own_write_scenarios(access: ScopedAccess) -> None:
        # Scenario 1: Write then immediate read
        for e, val in access(TestValue):
            access[e, TestValue] = TestValue(val.value + 1)
            updated = access[e, TestValue]
            seen_values.append(("immediate_read", updated.value if updated else None))

        # Scenario 2: Multiple sequential writes
        access[entity, TestValue] = TestValue(20)
        assert access[entity, TestValue].value == 20  # type: ignore
        access[entity, TestValue] = TestValue(30)
        assert access[entity, TestValue].value == 30  # type: ignore
        seen_values.append(("sequential_writes", 30))

        # Scenario 3: Query after own write
        access[entity, TestValue] = TestValue(42)
        results = list(access(TestValue))
        seen_values.append(("query_after_write", results[0][1].value))

    world.register_system(test_all_own_write_scenarios)
    world.tick()

    assert seen_values == [
        ("immediate_read", 11),
        ("sequential_writes", 30),
        ("query_after_write", 42),
    ]


def test_system_does_not_see_other_system_writes_same_tick(world):
    """CRITICAL: System2 doesn't see System1's writes in same tick.

    Why: Snapshot isolation prevents race conditions.
    """
    entity = world.spawn(TestValue(10))

    system1_executed = False
    system2_saw_value = None

    @system(reads=(TestValue,), writes=(TestValue,))
    def system1_writes(access: ScopedAccess) -> None:
        nonlocal system1_executed
        access[entity, TestValue] = TestValue(99)
        system1_executed = True

    @system(reads=(TestValue,), writes=())
    def system2_reads(access: ScopedAccess) -> None:
        nonlocal system2_saw_value
        # This runs after system1 in same tick
        val = access[entity, TestValue]
        system2_saw_value = val.value if val else None

    world.register_system(system1_writes)
    world.register_system(system2_reads)
    world.tick()

    assert system1_executed
    assert system2_saw_value == 10, "System2 should see original value, not System1's write"


def test_other_system_writes_visible_after_tick(world):
    """System sees other systems' writes after tick boundary."""
    entity = world.spawn(TestValue(10))

    @system(reads=(TestValue,), writes=(TestValue,))
    def writer(access: ScopedAccess) -> None:
        access[entity, TestValue] = TestValue(99)

    @system(reads=(TestValue,), writes=())
    def reader(access: ScopedAccess) -> None:
        val = access[entity, TestValue]
        assert val.value == 99 if val else False, "Should see write from previous tick"  # type: ignore

    world.register_system(writer)
    world.tick()  # Writer changes value

    world.register_system(reader)
    world.tick()  # Reader sees changed value


# Access control enforcement tests - prevents violating declared access


def test_cannot_read_undeclared_component(world):
    """System cannot read component not in reads declaration.

    Why: Enforces access patterns for parallelization safety.
    """
    entity = world.spawn(TestValue(10), OtherValue(20))

    @system(reads=(TestValue,), writes=())  # Only declared TestValue!
    def try_read_undeclared(access: ScopedAccess) -> None:
        _ = access[entity, OtherValue]  # Should raise!

    world.register_system(try_read_undeclared)

    with pytest.raises(AccessViolationError, match="not in readable types"):
        world.tick()


def test_cannot_write_undeclared_component(world):
    """System cannot write component not in writes declaration."""
    entity = world.spawn(TestValue(10), OtherValue(20))

    @system(reads=(TestValue,), writes=(TestValue,))  # Only writes TestValue!
    def try_write_undeclared(access: ScopedAccess) -> None:
        access[entity, OtherValue] = OtherValue(99)  # Should raise!

    world.register_system(try_write_undeclared)

    with pytest.raises(AccessViolationError, match="not in writable types"):
        world.tick()


def test_dev_mode_can_access_anything(world):
    """Dev mode systems bypass access control."""
    entity = world.spawn(TestValue(10), OtherValue(20))

    values_seen = []

    @system.dev()
    def dev_reads_everything(access: ScopedAccess) -> None:
        # Can read anything in dev mode
        val1 = access[entity, TestValue]
        val2 = access[entity, OtherValue]

        values_seen.extend([val1.value if val1 else None, val2.value if val2 else None])  # type: ignore

        # Can write anything too
        access[entity, TestValue] = TestValue(99)

    world.register_system(dev_reads_everything)
    world.tick()

    assert values_seen == [10, 20]
    assert world.get(entity, TestValue).value == 99  # type: ignore


def test_write_implies_read_access(world):
    """System can read components it can write."""
    entity = world.spawn(TestValue(10))

    read_value = None

    @system(reads=(), writes=(TestValue,))  # Only writes, not reads
    def write_implies_read(access: ScopedAccess) -> None:
        nonlocal read_value
        # Should be able to read TestValue (write implies read)
        val = access[entity, TestValue]
        read_value = val.value if val else None

    world.register_system(write_implies_read)
    world.tick()

    assert read_value == 10


# Query iteration snapshot consistency tests


def test_query_sees_initial_snapshot(world):
    """Query sees snapshot at start of system, not mid-iteration changes."""
    e1 = world.spawn(TestValue(1))
    e2 = world.spawn(TestValue(2))
    e3 = world.spawn(TestValue(3))

    seen_values = []

    @system(reads=(TestValue,), writes=(TestValue,))
    def modify_during_iteration(access: ScopedAccess) -> None:
        for entity, val in access(TestValue):
            seen_values.append(val.value)

            # Modify during iteration - shouldn't affect current iteration
            access[entity, TestValue] = TestValue(val.value * 10)

    world.register_system(modify_during_iteration)
    world.tick()

    # Should see original values during iteration
    assert sorted(seen_values) == [1, 2, 3]

    # But modifications are applied after tick
    assert world.get(e1, TestValue).value == 10  # type: ignore
    assert world.get(e2, TestValue).value == 20  # type: ignore
    assert world.get(e3, TestValue).value == 30  # type: ignore


# Result validation tests


def test_cannot_return_undeclared_writes(world):
    """System cannot return writes for undeclared components."""
    entity = world.spawn(TestValue(10))

    @system(reads=(TestValue,), writes=(TestValue,))  # Only writes TestValue
    def return_undeclared_write(access: ScopedAccess) -> dict:
        # Try to return write for OtherValue (not declared!)
        return {entity: {OtherValue: OtherValue(99)}}

    world.register_system(return_undeclared_write)

    with pytest.raises(
        (AccessViolationError, RuntimeError), match="not in writable types|writable_types"
    ):
        world.tick()


# Read-only mode tests


def test_readonly_system_cannot_write(world):
    """Read-only systems cannot write components."""
    entity = world.spawn(TestValue(10))

    @system.readonly(reads=(TestValue,))
    def readonly_tries_write(access: ScopedAccess) -> None:
        access[entity, TestValue] = TestValue(99)

    world.register_system(readonly_tries_write)

    # Should raise because readonly systems can't write
    with pytest.raises(AccessViolationError):
        world.tick()
