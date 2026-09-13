"""Scheduling models and configuration.

Types for execution planning and scheduler configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agentecs.models.system import SystemDescriptor


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
