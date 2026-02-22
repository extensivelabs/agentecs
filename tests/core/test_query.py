"""Tests for query system."""

from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from agentecs import Query, component
from agentecs.core.query import (
    AllAccess,
    NoAccess,
    TypeAccess,
    normalize_access,
    normalize_reads_and_writes,
    queries_disjoint,
)


# Test component types for queries
@component
@dataclass
class CompA:
    value: int


@component
@dataclass
class CompB:
    value: int


@component
@dataclass
class CompC:
    value: int


@component
@dataclass
class CompD:
    value: int


component_types = [CompA, CompB, CompC, CompD]


@st.composite
def query_strategy(draw):
    """Generate random queries for property testing."""
    # Pick 1-3 required components
    num_required = draw(st.integers(min_value=1, max_value=3))
    required = draw(
        st.lists(
            st.sampled_from(component_types),
            min_size=num_required,
            max_size=num_required,
            unique=True,
        )
    )

    # Pick 0-2 excluded components (different from required)
    available_excluded = [c for c in component_types if c not in required]
    if available_excluded:
        num_excluded = draw(st.integers(min_value=0, max_value=min(2, len(available_excluded))))
        excluded = draw(
            st.lists(
                st.sampled_from(available_excluded),
                min_size=num_excluded,
                max_size=num_excluded,
                unique=True,
            )
        )
    else:
        excluded = []

    q = Query(*required)
    for exc in excluded:
        q = q.excluding(exc)

    return q


# Query disjointness tests - critical for safe parallelization


def test_disjoint_if_required_is_excluded():
    """CRITICAL: Queries are disjoint if q1 requires what q2 excludes.

    Why: This is the definition of disjointness. False positive = race condition.
    """
    q1 = Query(CompA, CompB)
    q2 = Query(CompC).excluding(CompA)

    assert queries_disjoint(q1, q2), "q1 requires CompA which q2 excludes"


@given(q1=query_strategy(), q2=query_strategy())
def test_disjointness_soundness(q1, q2):
    """PROPERTY: If queries_disjoint returns True, no entity can match both.

    This is the critical safety property. False positive = race condition.
    """
    if not queries_disjoint(q1, q2):
        return  # Not claimed to be disjoint, skip

    # Claimed disjoint - verify no entity can match both
    # Try all possible combinations of the component types
    from itertools import chain, combinations

    def powerset(iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    for combo in powerset(component_types):
        archetype = frozenset(combo)

        # If both match, queries_disjoint lied!
        both_match = q1.matches_archetype(archetype) and q2.matches_archetype(archetype)

        assert not both_match, (
            f"INVARIANT VIOLATED: queries_disjoint({q1}, {q2}) returned True "
            f"but both match archetype {archetype}"
        )


@given(q1=query_strategy(), q2=query_strategy())
def test_disjointness_definition(q1, q2):
    """PROPERTY: Queries are disjoint iff one requires what the other excludes."""
    is_disjoint = queries_disjoint(q1, q2)

    # Check definition: q1 requires something q2 excludes, or vice versa
    q1_requires_q2_excludes = any(t in q2.excluded for t in q1.required)
    q2_requires_q1_excludes = any(t in q1.excluded for t in q2.required)

    expected_disjoint = q1_requires_q2_excludes or q2_requires_q1_excludes

    assert is_disjoint == expected_disjoint, (
        f"Disjointness check inconsistent with definition: "
        f"queries_disjoint={is_disjoint}, expected={expected_disjoint}"
    )


# Query archetype matching tests - critical for storage backends


def test_matches_if_has_all_required():
    """Query matches if archetype has all required components."""
    q = Query(CompA, CompB)
    archetype = frozenset([CompA, CompB, CompC])

    assert q.matches_archetype(archetype)


def test_no_match_if_missing_required():
    """Query doesn't match if archetype missing required component."""
    q = Query(CompA, CompB)
    archetype = frozenset([CompA, CompC])  # Missing CompB

    assert not q.matches_archetype(archetype)


def test_no_match_if_has_excluded():
    """Query doesn't match if archetype has excluded component."""
    q = Query(CompA).excluding(CompB)
    archetype = frozenset([CompA, CompB])

    assert not q.matches_archetype(archetype)


def test_matches_if_excluded_not_present():
    """Query matches if excluded component is not in archetype."""
    q = Query(CompA).excluding(CompB)
    archetype = frozenset([CompA, CompC])  # No CompB

    assert q.matches_archetype(archetype)


@given(q=query_strategy())
def test_archetype_matching_soundness(q):
    """PROPERTY: If matches_archetype returns True, entity actually matches.

    This is a soundness property - no false positives.
    """
    from itertools import chain, combinations

    def powerset(iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    for combo in powerset(component_types):
        archetype = frozenset(combo)

        if not q.matches_archetype(archetype):
            continue  # Doesn't match, skip

        # If matches_archetype says yes, verify manually
        has_all_required = all(t in archetype for t in q.required)
        has_no_excluded = all(t not in archetype for t in q.excluded)

        assert has_all_required and has_no_excluded, (
            f"matches_archetype returned True but manual check fails: "
            f"query={q}, archetype={archetype}"
        )


# Query builder tests


def test_query_having_adds_requirements():
    """having() adds to required components."""
    q = Query(CompA).having(CompB)

    assert CompA in q.required
    assert CompB in q.required


def test_query_excluding_adds_exclusions():
    """excluding() adds to excluded components."""
    q = Query(CompA).excluding(CompB)

    assert CompA in q.required
    assert CompB in q.excluded


def test_query_chaining():
    """Query methods can be chained."""
    q = Query(CompA).having(CompB).excluding(CompC).excluding(CompD)

    assert q.required == (CompA, CompB)
    assert CompC in q.excluded
    assert CompD in q.excluded


def test_query_immutable():
    """Query methods return new instances (immutable)."""
    q1 = Query(CompA)
    q2 = q1.having(CompB)

    assert q1.required == (CompA,)
    assert q2.required == (CompA, CompB)
    assert q1 is not q2


@pytest.mark.parametrize(
    ("input_val", "expected_type", "check_fn"),
    [
        (
            (CompA, CompB),
            TypeAccess,
            lambda p: p.types == frozenset([CompA, CompB]),
        ),
        (
            Query(CompA).excluding(CompB),
            "QueryAccess",
            lambda p: Query(CompA).excluding(CompB).required == (CompA,),
        ),
        (
            AllAccess(),
            AllAccess,
            lambda p: True,
        ),
    ],
    ids=["type_tuple", "query", "allaccess"],
)
def test_normalize_access_variants(input_val, expected_type, check_fn):
    """normalize_access returns correct type for each input variant."""
    from agentecs.core.query import QueryAccess

    pattern = normalize_access(input_val)

    if expected_type == "QueryAccess":
        assert isinstance(pattern, QueryAccess)
    else:
        assert isinstance(pattern, expected_type)
    assert check_fn(pattern)


def test_normalize_access_empty_tuple_returns_no_access():
    """normalize_access(()) returns NoAccess."""
    pattern = normalize_access(())

    assert isinstance(pattern, NoAccess)


def test_normalize_access_none_returns_all_access():
    """normalize_access(None) returns AllAccess."""
    pattern = normalize_access(None)

    assert isinstance(pattern, AllAccess)


def test_normalize_reads_and_writes_defaults_full_when_both_omitted():
    """normalize_reads_and_writes(None, None) gives unrestricted access."""
    reads, writes = normalize_reads_and_writes(None, None)

    assert isinstance(reads, AllAccess)
    assert isinstance(writes, AllAccess)


def test_normalize_reads_and_writes_defaults_missing_side_to_no_access():
    """When one side is omitted, the omitted side normalizes to NoAccess."""
    reads, writes = normalize_reads_and_writes((CompA,), None)

    assert isinstance(reads, TypeAccess)
    assert reads.types == frozenset([CompA])
    assert isinstance(writes, NoAccess)

    reads2, writes2 = normalize_reads_and_writes(None, (CompB,))

    assert isinstance(reads2, NoAccess)
    assert isinstance(writes2, TypeAccess)
    assert writes2.types == frozenset([CompB])
