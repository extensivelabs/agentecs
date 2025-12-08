"""Query operations and access pattern utilities."""

from __future__ import annotations

from typing import cast

from agentecs.core.query.models import AccessPattern, AllAccess, Query, QueryAccess, TypeAccess


def queries_disjoint(q1: Query, q2: Query) -> bool:
    """Check if two queries can never match the same entity.

    Queries are disjoint if one requires a component type that the other excludes.
    Used by scheduler to determine if systems can run in parallel even when both
    write the same component type.

    Args:
        q1: First query to check.
        q2: Second query to check.

    Returns:
        True if queries can never match the same entity, False otherwise.
    """
    # Disjoint if q1 requires something q2 excludes, or vice versa
    return any(t in q2.excluded for t in q1.required) or any(t in q1.excluded for t in q2.required)


def normalize_access(spec: tuple[type, ...] | Query | AllAccess | None) -> AccessPattern:
    """Convert various access specifications to normalized AccessPattern.

    Handles multiple input formats:
    - None or empty tuple -> TypeAccess with no types
    - AllAccess -> passthrough
    - Single Query -> QueryAccess
    - Tuple of types -> TypeAccess
    - Tuple of queries -> QueryAccess

    Args:
        spec: Access specification in various formats.

    Returns:
        Normalized AccessPattern (AllAccess, TypeAccess, or QueryAccess).

    Raises:
        TypeError: If spec is not a recognized access specification format.
    """
    if spec is None or spec == ():
        return TypeAccess(frozenset())
    if isinstance(spec, AllAccess):
        return spec
    if isinstance(spec, Query):
        return QueryAccess(queries=(spec,))
    if isinstance(spec, tuple):
        # Check if tuple of types or tuple of queries
        if all(isinstance(t, type) for t in spec):
            return TypeAccess(frozenset(spec))
        if all(isinstance(t, Query) for t in spec):
            return QueryAccess(queries=cast(tuple[Query, ...], spec))
    raise TypeError(f"Invalid access specification: {spec}")
