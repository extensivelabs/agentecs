"""Query models and access patterns.

Usage:
    # Type-level (all entities with these components)
    @system(reads=(Position, Velocity), writes=(Position,))

    # Query-level (fine-grained archetype filtering)
    @system(
        reads=Query(Position, Velocity).having(PlayerTag),
        writes=Query(Position).having(PlayerTag),
    )

    # Exclusions
    @system(reads=Query(Position).excluding(FrozenTag))
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    """Declarative query for access pattern declarations.

    Immutable - each method returns a new Query instance.
    """

    required: tuple[type, ...] = ()
    excluded: tuple[type, ...] = ()

    def __init__(self, *required: type):
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "excluded", ())

    def having(self, *types: type) -> Query:
        """Entities must also have these component types."""
        new = Query(*self.required, *types)
        object.__setattr__(new, "excluded", self.excluded)
        return new

    def excluding(self, *types: type) -> Query:
        """Entities must NOT have these component types."""
        new = Query(*self.required)
        object.__setattr__(new, "excluded", self.excluded + types)
        return new

    def __iter__(self) -> Iterator[type]:
        """Allow Query to be used where tuple of types expected."""
        return iter(self.required)

    def __contains__(self, item: type) -> bool:
        return item in self.required

    def types(self) -> frozenset[type]:
        """All types this query accesses (required only)."""
        return frozenset(self.required)

    def matches_archetype(self, has: frozenset[type]) -> bool:
        """Check if an archetype (set of component types) matches this query."""
        return all(t in has for t in self.required) and all(t not in has for t in self.excluded)


@dataclass(frozen=True)
class AllAccess:
    """Unrestricted component access."""

    pass


@dataclass(frozen=True)
class NoAccess:
    """No component access."""

    pass


@dataclass(frozen=True)
class TypeAccess:
    """Access to all entities with certain component types."""

    types: frozenset[type]

    def __init__(self, types: tuple[type, ...] | frozenset[type]):
        object.__setattr__(self, "types", frozenset(types) if isinstance(types, tuple) else types)


@dataclass(frozen=True)
class QueryAccess:
    """Access only to entities matching query patterns."""

    queries: tuple[Query, ...]

    def types(self) -> frozenset[type]:
        """All component types accessed by any query."""
        result: set[type] = set()
        for q in self.queries:
            result.update(q.required)
        return frozenset(result)


AccessPattern = AllAccess | TypeAccess | QueryAccess | NoAccess
