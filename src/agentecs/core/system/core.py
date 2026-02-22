"""System decorator and access control.

Usage:
    # System with no access declarations (full access, runs in parallel)
    @system()
    def full_access_system(world: ScopedAccess) -> None:
        # Can read/write any component, still runs in parallel with others
        ...

    # System with declared access (validated at runtime)
    @system(reads=(Position, Velocity), writes=(Position,))
    def movement(world: ScopedAccess) -> None:
        for entity, pos, vel in world(Position, Velocity):
            world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)

    # Dev mode - unrestricted access, runs in isolation (for debugging)
    @system.dev()
    def debug_inspector(world: ScopedAccess) -> None:
        # Full access AND runs alone in its own execution group
        ...

    # Pure mode - must return changes, no world.update()
    @system(reads=(A,), writes=(B,), mode=SystemMode.PURE)
    def pure_transform(world: ReadOnlyAccess) -> dict[EntityId, dict[type, Any]]:
        return {e: {B: B(a.value)} for e, (a,) in world.query(A)}
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from agentecs.core.query import (
    AllAccess,
    NoAccess,
    Query,
    normalize_access,
    normalize_reads_and_writes,
)
from agentecs.core.system.models import SystemDescriptor, SystemMode


class _SystemDecorator:
    """System decorator factory. Used as @system(...) or @system.dev()."""

    def __call__(
        self,
        reads: tuple[type, ...] | tuple[Query, ...] | Query | AllAccess | NoAccess | None = None,
        writes: tuple[type, ...] | tuple[Query, ...] | Query | AllAccess | NoAccess | None = None,
        mode: SystemMode = SystemMode.INTERACTIVE,
        frequency: float = 1.0,
        phase: str = "update",
    ) -> Callable[[Callable[..., Any]], SystemDescriptor]:
        """Register system with optional access patterns.

        If both reads and writes are None (default), system has full access
        but still participates in parallel execution (unlike dev mode which
        runs in isolation).

        If either is specified, the other defaults to empty (no access).

        TODO: Implement dependency specification to enforce system ordering.

        Usage:
            # System with declared access
            @system(reads=(Position, Velocity), writes=(Position,))
            def movement_system(world): ...

            # Pure mode system
            # Returns changes instead of mutating world
            @system(reads=(A,), writes=(B,), mode=SystemMode.PURE)
            def pure_transform_system(world): ...


        Args:
            reads: Component types or Query the system reads.
            writes: Component types or Query the system writes.
            mode: System execution mode (INTERACTIVE, PURE, READONLY).
                Defaults to INTERACTIVE. Options:
                INTERACTIVE: System can read and write declared components,
                    mutates local world view during run.
                PURE: System must return changes instead of mutating view of world,
                    for deterministic execution.
                READONLY: System can only read declared components, cannot write.
            frequency: How often the system runs (times per second).
            phase: Execution phase the system belongs to (e.g. "update", "render").

        Returns:
            Decorator that registers the system and returns its descriptor.
        """

        def decorator(fn: Callable[..., Any]) -> SystemDescriptor:
            if mode == SystemMode.READONLY and writes not in (None, (), NoAccess()):
                raise ValueError("READONLY systems cannot declare writes")

            reads_access, writes_access = normalize_reads_and_writes(reads, writes)
            if mode == SystemMode.READONLY:
                writes_access = NoAccess()

            return SystemDescriptor(
                name=fn.__name__,
                run=fn,
                reads=reads_access,
                writes=writes_access,
                mode=mode,
                is_async=inspect.iscoroutinefunction(fn),
                frequency=frequency,
                phase=phase,
            )

        return decorator

    def dev(
        self,
        frequency: float = 1.0,
        phase: str = "update",
    ) -> Callable[[Callable[..., Any]], SystemDescriptor]:
        """Dev mode: unrestricted access, runs in isolation (cannot parallelize).

        Usage:
            @system.dev()
            def debug_system(world): ...

        Unlike @system() with no args (which has full access but runs in parallel),
        dev mode systems run in their own execution group for debugging isolation.
        """

        def decorator(fn: Callable[..., Any]) -> SystemDescriptor:
            return SystemDescriptor(
                name=fn.__name__,
                run=fn,
                reads=AllAccess(),
                writes=AllAccess(),
                mode=SystemMode.INTERACTIVE,
                is_async=inspect.iscoroutinefunction(fn),
                frequency=frequency,
                phase=phase,
                runs_alone=True,  # Dev mode runs in isolation
            )

        return decorator

    def readonly(
        self,
        reads: tuple[type, ...] | Query | None = None,
        frequency: float = 1.0,
        phase: str = "update",
    ) -> Callable[[Callable[..., Any]], SystemDescriptor]:
        """Read-only system (observers, loggers).

        Usage:
            @system.readonly(reads=(Metrics,))
            def logger(world): ...
        """

        def decorator(fn: Callable[..., Any]) -> SystemDescriptor:
            return SystemDescriptor(
                name=fn.__name__,
                run=fn,
                reads=normalize_access(reads),
                writes=NoAccess(),
                mode=SystemMode.READONLY,
                is_async=inspect.iscoroutinefunction(fn),
                frequency=frequency,
                phase=phase,
            )

        return decorator


system = _SystemDecorator()


def check_read_access(
    descriptor: SystemDescriptor,
    component_type: type,
) -> bool:
    """Check if system is allowed to read this component type."""
    if descriptor.is_dev_mode():
        return True
    return descriptor.can_read_type(component_type)


def check_write_access(
    descriptor: SystemDescriptor,
    component_type: type,
) -> bool:
    """Check if system is allowed to write this component type."""
    if descriptor.is_dev_mode():
        return True
    if descriptor.mode == SystemMode.READONLY:
        return False
    return descriptor.can_write_type(component_type)
