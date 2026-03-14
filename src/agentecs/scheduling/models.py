"""Scheduling models and configuration.

Types for execution planning and scheduler configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from agentecs.core.system import SystemDescriptor


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for retrying failed system executions.

    Useful for systems that call external APIs with transient failures.
    """

    max_attempts: int = 1
    """Maximum attempts (1 = no retry). Default: no retry."""

    backoff: Literal["none", "linear", "exponential"] = "none"
    """Backoff strategy between retries."""

    base_delay: float = 0.1
    """Base delay in seconds for backoff calculation."""

    on_exhausted: Literal["fail", "skip"] = "fail"
    """What to do when retries exhausted: fail tick or skip system's results."""


@dataclass
class ExecutionGroup:
    """Group of systems to execute in parallel.

    All systems in a group see the same initial state (snapshot isolation).
    Results are merged after group execution completes.
    """

    systems: list[SystemDescriptor] = field(default_factory=list)
    """Systems to execute concurrently."""


# Type alias for execution plans
ExecutionPlan = list[ExecutionGroup]
"""Ordered list of execution groups. Groups run sequentially, systems within in parallel."""


@dataclass
class SchedulerConfig:
    """Configuration for scheduler behavior.

    Passed to scheduler at construction or via World.
    """

    max_concurrent: int | None = None
    """Max concurrent system executions. None = unlimited (default)."""

    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    """Retry policy for failed system executions. Default: no retry."""


# --- Execution Group Builders ---
# Protocols and implementations for building execution plans from registered systems.
# This is the extension point for future scheduling strategies.

if TYPE_CHECKING:
    from typing import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable


@runtime_checkable
class ExecutionGroupBuilder(Protocol):
    """Protocol for building execution plans from registered systems.

    Extension point for scheduling strategies. Implementations determine how
    systems are grouped for execution. Groups execute sequentially; systems
    within groups execute in parallel.

    Built-in implementations:
    - SingleGroupBuilder: All systems in one group (default)

    Future implementations (not yet built):
    - DependencyGroupBuilder: Groups based on depends_on declarations
    - FrequencyGroupBuilder: Groups based on tick frequency
    - ConditionGroupBuilder: Groups based on runtime conditions
    """

    def build(self, systems: list[SystemDescriptor]) -> ExecutionPlan:
        """Build execution plan from registered systems.

        Args:
            systems: All registered systems in registration order.

        Returns:
            ExecutionPlan (list of ExecutionGroups) defining execution order.
        """
        ...


class SingleGroupBuilder:
    """Default builder: all systems in one group, dev systems isolated.

    Creates two types of groups:
    1. One group per dev system (runs alone, first)
    2. One group for all normal systems (runs in parallel)

    This provides maximum parallelism while respecting dev mode isolation.
    """

    def build(self, systems: list[SystemDescriptor]) -> ExecutionPlan:
        """Build plan with dev systems isolated, others grouped."""
        dev_systems: list[SystemDescriptor] = []
        normal_systems: list[SystemDescriptor] = []

        for system in systems:
            if system.is_dev_mode():
                dev_systems.append(system)
            else:
                normal_systems.append(system)

        groups: ExecutionPlan = []

        # Dev systems each get their own group (run sequentially, alone)
        for dev_system in dev_systems:
            groups.append(ExecutionGroup(systems=[dev_system]))

        # All normal systems in one group (run in parallel)
        if normal_systems:
            groups.append(ExecutionGroup(systems=normal_systems))

        return groups
