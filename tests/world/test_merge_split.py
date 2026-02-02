"""Tests for entity merge and split operations."""

from dataclasses import dataclass

import pytest

from agentecs import (
    NonMergeableHandling,
    NonSplittableHandling,
    World,
    component,
)


@component
@dataclass(slots=True)
class MergeablePosition:
    """Position component with merge support."""

    x: float
    y: float

    def __merge__(self, other: "MergeablePosition") -> "MergeablePosition":
        """Merge by averaging positions."""
        return MergeablePosition(
            x=(self.x + other.x) / 2,
            y=(self.y + other.y) / 2,
        )


@component
@dataclass(slots=True)
class SplittableCredits:
    """Credits component with split support."""

    amount: float

    def __merge__(self, other: "SplittableCredits") -> "SplittableCredits":
        """Merge by summing credits."""
        return SplittableCredits(amount=self.amount + other.amount)

    def __split__(self, ratio: float = 0.5) -> tuple["SplittableCredits", "SplittableCredits"]:
        """Split credits by ratio."""
        left_amount = self.amount * ratio
        right_amount = self.amount * (1 - ratio)
        return SplittableCredits(left_amount), SplittableCredits(right_amount)


@component
@dataclass(slots=True)
class NonMergeableTag:
    """Simple tag without merge support."""

    name: str


@component
@dataclass(slots=True)
class NonSplittableHealth:
    """Health without split support."""

    hp: int


class TestMergeEntities:
    """Tests for World.merge_entities()."""

    def test_merge_with_mergeable_components(self) -> None:
        """Mergeable components are merged via __merge__."""
        world = World()
        e1 = world.spawn(MergeablePosition(0, 0))
        e2 = world.spawn(MergeablePosition(10, 20))

        merged = world.merge_entities(e1, e2)

        pos = world.get(merged, MergeablePosition)
        assert pos is not None
        assert pos.x == 5.0  # (0 + 10) / 2
        assert pos.y == 10.0  # (0 + 20) / 2

    def test_merge_destroys_original_entities(self) -> None:
        """Original entities are destroyed after merge."""
        world = World()
        e1 = world.spawn(MergeablePosition(0, 0))
        e2 = world.spawn(MergeablePosition(10, 10))

        merged = world.merge_entities(e1, e2)

        # Original entities should not exist
        assert world.get(e1, MergeablePosition) is None
        assert world.get(e2, MergeablePosition) is None
        # Merged entity should exist
        assert world.get(merged, MergeablePosition) is not None

    def test_merge_combines_different_components(self) -> None:
        """Components unique to one entity are included in merged."""
        world = World()
        e1 = world.spawn(MergeablePosition(0, 0), NonMergeableTag("alice"))
        e2 = world.spawn(MergeablePosition(10, 10), NonSplittableHealth(100))

        merged = world.merge_entities(e1, e2)

        # All components should be present
        assert world.get(merged, MergeablePosition) is not None
        assert world.get(merged, NonMergeableTag) is not None
        assert world.get(merged, NonSplittableHealth) is not None

    @pytest.mark.parametrize(
        ("handling", "expected_name"),
        [
            (NonMergeableHandling.FIRST, "alice"),
            (NonMergeableHandling.SECOND, "bob"),
            (NonMergeableHandling.SKIP, None),
        ],
    )
    def test_merge_non_mergeable_handling(
        self, handling: NonMergeableHandling, expected_name: str | None
    ) -> None:
        """Non-mergeable handling strategies work correctly."""
        world = World()
        e1 = world.spawn(NonMergeableTag("alice"))
        e2 = world.spawn(NonMergeableTag("bob"))

        merged = world.merge_entities(e1, e2, on_non_mergeable=handling)

        tag = world.get(merged, NonMergeableTag)
        if expected_name is None:
            assert tag is None
        else:
            assert tag is not None
            assert tag.name == expected_name

    def test_merge_non_mergeable_error(self) -> None:
        """Non-mergeable with ERROR raises TypeError."""
        world = World()
        e1 = world.spawn(NonMergeableTag("alice"))
        e2 = world.spawn(NonMergeableTag("bob"))

        with pytest.raises(TypeError, match="not Mergeable"):
            world.merge_entities(e1, e2, on_non_mergeable=NonMergeableHandling.ERROR)

    def test_merge_nonexistent_entity_raises(self) -> None:
        """Merging nonexistent entity raises ValueError."""
        world = World()
        e1 = world.spawn(MergeablePosition(0, 0))
        world.destroy(e1)

        e2 = world.spawn(MergeablePosition(10, 10))

        with pytest.raises(ValueError, match="does not exist"):
            world.merge_entities(e1, e2)


class TestSplitEntity:
    """Tests for World.split_entity()."""

    def test_split_with_splittable_components(self) -> None:
        """Splittable components are split via __split__."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity, ratio=0.7)

        left_credits = world.get(left, SplittableCredits)
        right_credits = world.get(right, SplittableCredits)
        assert left_credits is not None
        assert right_credits is not None
        assert left_credits.amount == pytest.approx(70.0)
        assert right_credits.amount == pytest.approx(30.0)

    def test_split_destroys_original_entity(self) -> None:
        """Original entity is destroyed after split."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity)

        # Original should not exist
        assert world.get(entity, SplittableCredits) is None
        # Split entities should exist
        assert world.get(left, SplittableCredits) is not None
        assert world.get(right, SplittableCredits) is not None

    @pytest.mark.parametrize(
        ("handling", "left_has", "right_has"),
        [
            (NonSplittableHandling.BOTH, True, True),
            (NonSplittableHandling.FIRST, True, False),
            (NonSplittableHandling.SKIP, False, False),
        ],
    )
    def test_split_non_splittable_handling(
        self, handling: NonSplittableHandling, left_has: bool, right_has: bool
    ) -> None:
        """Non-splittable handling strategies work correctly."""
        world = World()
        entity = world.spawn(NonSplittableHealth(100))

        left, right = world.split_entity(entity, on_non_splittable=handling)

        left_hp = world.get(left, NonSplittableHealth)
        right_hp = world.get(right, NonSplittableHealth)

        if left_has:
            assert left_hp is not None and left_hp.hp == 100
        else:
            assert left_hp is None

        if right_has:
            assert right_hp is not None and right_hp.hp == 100
        else:
            assert right_hp is None

    def test_split_non_splittable_error(self) -> None:
        """Non-splittable with ERROR raises TypeError."""
        world = World()
        entity = world.spawn(NonSplittableHealth(100))

        with pytest.raises(TypeError, match="not Splittable"):
            world.split_entity(entity, on_non_splittable=NonSplittableHandling.ERROR)

    def test_split_invalid_ratio_raises(self) -> None:
        """Invalid ratio raises ValueError."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            world.split_entity(entity, ratio=1.5)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            world.split_entity(entity, ratio=-0.1)

    def test_split_nonexistent_entity_raises(self) -> None:
        """Splitting nonexistent entity raises ValueError."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))
        world.destroy(entity)

        with pytest.raises(ValueError, match="does not exist"):
            world.split_entity(entity)

    def test_split_equal_ratio(self) -> None:
        """Default 0.5 ratio splits equally."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity)

        left_credits = world.get(left, SplittableCredits)
        right_credits = world.get(right, SplittableCredits)
        assert left_credits is not None and left_credits.amount == 50.0
        assert right_credits is not None and right_credits.amount == 50.0


class TestMergeSplitRoundtrip:
    """Tests verifying merge and split are compatible."""

    def test_split_then_merge_restores_value(self) -> None:
        """Splitting then merging should restore original value."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity)
        merged = world.merge_entities(left, right)

        credits = world.get(merged, SplittableCredits)
        assert credits is not None
        assert credits.amount == 100.0  # 50 + 50

    def test_multiple_splits_and_merges(self) -> None:
        """Multiple splits and merges maintain consistency."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        # Split into 4
        l1, r1 = world.split_entity(entity)
        l2, l3 = world.split_entity(l1)
        r2, r3 = world.split_entity(r1)

        # Each should have 25
        for e in [l2, l3, r2, r3]:
            c = world.get(e, SplittableCredits)
            assert c is not None and c.amount == 25.0

        # Merge back
        m1 = world.merge_entities(l2, l3)
        m2 = world.merge_entities(r2, r3)
        final = world.merge_entities(m1, m2)

        credits = world.get(final, SplittableCredits)
        assert credits is not None
        assert credits.amount == 100.0
