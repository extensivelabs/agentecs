"""Public decorators for declaring components and systems.

Usage:
    @component
    @dataclass(slots=True)
    class Position:
        x: float
        y: float

    # System with no access declarations (full access, runs in parallel)
    @system()
    def full_access_system(world: ScopedAccess) -> None:
        ...

    # System with declared access (validated at runtime)
    @system(reads=(Position, Velocity), writes=(Position,))
    def movement(world: ScopedAccess) -> None:
        for entity, pos, vel in world(Position, Velocity):
            world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)

    # Dev mode - unrestricted access, runs in isolation (for debugging)
    @system.dev()
    def debug_inspector(world: ScopedAccess) -> None:
        ...

    # Pure mode - must return changes, no world.update()
    @system(reads=(A,), writes=(B,), mode=SystemMode.PURE)
    def pure_transform(world: ReadOnlyAccess) -> dict[EntityId, dict[type, Any]]:
        return {e: {B: B(a.value)} for e, (a,) in world.query(A)}
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import is_dataclass
from typing import Any, overload

from agentecs.functions.component import is_pydantic
from agentecs.functions.query import normalize_access, normalize_reads_and_writes
from agentecs.models.query import AllAccess, NoAccess, Query
from agentecs.models.system import SystemDescriptor, SystemMode
from agentecs.services.registry import get_registry


@overload
def component(cls: type) -> type: ...


@overload
def component(cls: None = None) -> Callable[[type], type]: ...


def component(cls: type | None = None) -> type | Callable[[type], type]:
    """Register a dataclass or Pydantic model as a component type.

    Supports two forms:
        @component                    # bare decorator
        @component()                  # parenthesized, no args

    Args:
        cls: The class to register, or None if called with arguments.

    Returns:
        Decorated class or decorator function.

    Raises:
        TypeError: If class is neither a dataclass nor Pydantic model.

    Note:
        Apply @component AFTER @dataclass:

        >>> @component
        ... @dataclass(slots=True)
        ... class MyComponent:
        ...     value: int
    """

    def decorator(c: type) -> type:
        if not (is_dataclass(c) or is_pydantic(c)):
            raise TypeError(
                f"Component {c.__name__} must be a dataclass or Pydantic model. "
                f"Did you forget @dataclass decorator?"
            )
        meta = get_registry().register(c)
        c.__component_meta__ = meta  # type: ignore
        return c

    if cls is None:
        # Called with args: @component()
        return decorator
    else:
        # Called bare: @component
        return decorator(cls)


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
