"""System models: descriptors, modes, and access levels."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..query import AccessPattern


class SystemMode(Enum):
    """Execution mode controlling access capabilities."""

    INTERACTIVE = auto()  # Full ScopedAccess, writes during execution
    PURE = auto()  # ReadOnlyAccess, must return all changes
    READONLY = auto()  # ReadOnlyAccess, no writes allowed


class Access(Enum):
    """Access level for a component type."""

    READ = auto()
    WRITE = auto()


@dataclass(frozen=True)
class SystemDescriptor:
    """Metadata about a registered system."""

    name: str
    run: Callable[..., Any]
    reads: AccessPattern
    writes: AccessPattern
    mode: SystemMode
    is_async: bool = False
    frequency: float = 1.0
    phase: str = "update"
    runs_alone: bool = False  # If True, runs in its own execution group (dev mode)

    def readable_types(self) -> frozenset[type]:
        """Get all component types this system can read.

        Returns:
            Set of component types system has read or write access to.
            Write access implies read access.
        """
        r = self._extract_types(self.reads)
        w = self._extract_types(self.writes)
        return r | w  # Write implies read

    def writable_types(self) -> frozenset[type]:
        """Get all component types this system can write.

        Returns:
            Set of component types system has write access to.
        """
        return self._extract_types(self.writes)

    def _extract_types(self, pattern: AccessPattern) -> frozenset[type]:
        from agentecs.core.query.models import QueryAccess, TypeAccess

        if isinstance(pattern, TypeAccess):
            return pattern.types
        if isinstance(pattern, QueryAccess):
            return pattern.types()
        return frozenset()  # Sentinel: empty means "all"

    def is_dev_mode(self) -> bool:
        """Check if system should run in isolation (dev mode).

        Returns:
            True if system should run alone in its own execution group.
        """
        return self.runs_alone


if TYPE_CHECKING:
    from typing import Protocol, runtime_checkable
else:
    from typing import Protocol, runtime_checkable


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

    async def tick_async(self, world: Any) -> None:
        """Execute all registered systems once.

        Args:
            world: World instance providing execute_system_async() and apply_result()
        """
        ...
