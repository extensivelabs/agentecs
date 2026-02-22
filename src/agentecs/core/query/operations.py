"""Query operations and access pattern utilities."""

from __future__ import annotations

from typing import cast

from agentecs.core.query.models import (
    AccessPattern,
    AllAccess,
    NoAccess,
    Query,
    QueryAccess,
    TypeAccess,
)


def queries_disjoint(q1: Query, q2: Query) -> bool:
    """Check if two queries can never match the same entity.

    Queries are disjoint if one requires a component type that the other excludes.
    Used by scheduler to determine if systems can run in parallel even when both
    write the same component type.

    TODO: See if we still need this.

    Args:
        q1: First query to check.
        q2: Second query to check.

    Returns:
        True if queries can never match the same entity, False otherwise.
    """
    # Disjoint if q1 requires something q2 excludes, or vice versa
    return any(t in q2.excluded for t in q1.required) or any(t in q1.excluded for t in q2.required)


def normalize_access(
    spec: tuple[type, ...] | tuple[Query, ...] | Query | AllAccess | NoAccess | None,
) -> AccessPattern:
    """Convert various access specifications to normalized AccessPattern.

    Handles multiple input formats:
    - None -> AllAccess
    - Empty tuple -> NoAccess
    - AllAccess or NoAccess -> passthrough
    - Single Query -> QueryAccess
    - Tuple of types -> TypeAccess
    - Tuple of queries -> QueryAccess

    Args:
        spec: Access specification in various formats.

    Returns:
        Normalized AccessPattern (AllAccess, NoAccess, TypeAccess, or QueryAccess).

    Raises:
        TypeError: If spec is not a recognized access specification format.
    """
    if spec is None:
        return AllAccess()
    if isinstance(spec, (AllAccess, NoAccess)):
        return spec
    if isinstance(spec, Query):
        return QueryAccess(queries=(spec,))
    if isinstance(spec, tuple):
        if len(spec) == 0:
            return NoAccess()
        # Check if tuple of types or tuple of queries
        if all(isinstance(t, type) for t in spec):
            return TypeAccess(cast(tuple[type, ...], spec))
        if all(isinstance(t, Query) for t in spec):
            return QueryAccess(queries=cast(tuple[Query, ...], spec))
    raise TypeError(f"Invalid access specification: {spec}")


def normalize_reads_and_writes(
    reads: tuple[type, ...] | tuple[Query, ...] | Query | AllAccess | NoAccess | None,
    writes: tuple[type, ...] | tuple[Query, ...] | Query | AllAccess | NoAccess | None,
) -> tuple[AccessPattern, AccessPattern]:
    """Normalize reads and writes specifications to AccessPatterns.

    If reads and writes are None (not given), defaults to AllAccess.
    If either is given and the other is None, the other defaults to NoAccess.

    This ensures that reads=(A,) and writes=None is treated as reads=(A,) and
    writes=NoAccess(), avoiding accidental implicit write access.

    Args:
        reads: Access specification for reads.
        writes: Access specification for writes.

    Returns:
        Tuple of normalized AccessPatterns for reads and writes.
    """
    if reads is None and writes is None:
        return AllAccess(), AllAccess()
    parsed_reads = NoAccess() if reads is None else normalize_access(reads)
    parsed_writes = NoAccess() if writes is None else normalize_access(writes)
    return parsed_reads, parsed_writes
