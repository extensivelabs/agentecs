"""Tests for entity merge and split operations."""

from dataclasses import dataclass, field

import pytest

from agentecs import AccessViolationError, EntityId, ScopedAccess, World, component, system


@component
@dataclass(slots=True)
class CombinablePosition:
    """Position component with combine support."""

    x: float
    y: float

    def __combine__(self, other: "CombinablePosition") -> "CombinablePosition":
        """Combine by averaging positions."""
        return CombinablePosition(
            x=(self.x + other.x) / 2,
            y=(self.y + other.y) / 2,
        )


@component
@dataclass(slots=True)
class SplittableCredits:
    """Credits component with combine and split support."""

    amount: float

    def __combine__(self, other: "SplittableCredits") -> "SplittableCredits":
        """Combine by summing credits."""
        return SplittableCredits(amount=self.amount + other.amount)

    def __split__(self) -> tuple["SplittableCredits", "SplittableCredits"]:
        """Split credits equally."""
        half = self.amount / 2
        return SplittableCredits(half), SplittableCredits(self.amount - half)


@component
@dataclass(slots=True)
class PlainTag:
    """Simple tag without combine support."""

    name: str


@component
@dataclass(slots=True)
class PlainHealth:
    """Health without split support."""

    hp: int
    notes: list[str] = field(default_factory=list)


class TestMergeEntities:
    """Tests for World.merge_entities()."""

    def test_merge_entities_with_combinable(self) -> None:
        """Combinable components are combined via __combine__."""
        world = World()
        e1 = world.spawn(CombinablePosition(0, 0))
        e2 = world.spawn(CombinablePosition(10, 20))

        merged = world.merge_entities(e1, e2)

        pos = world.get_copy(merged, CombinablePosition)
        assert pos is not None
        assert pos.x == 5.0
        assert pos.y == 10.0

    def test_merge_entities_destroys_originals(self) -> None:
        """Original entities are destroyed after merge."""
        world = World()
        e1 = world.spawn(CombinablePosition(0, 0))
        e2 = world.spawn(CombinablePosition(10, 10))

        merged = world.merge_entities(e1, e2)

        assert world.get_copy(e1, CombinablePosition) is None
        assert world.get_copy(e2, CombinablePosition) is None
        assert world.get_copy(merged, CombinablePosition) is not None

    def test_merge_entities_combines_different_components(self) -> None:
        """Components unique to one entity are retained in merged entity."""
        world = World()
        e1 = world.spawn(CombinablePosition(0, 0), PlainTag("alice"))
        e2 = world.spawn(CombinablePosition(10, 10), PlainHealth(100, ["ok"]))

        merged = world.merge_entities(e1, e2)

        assert world.get_copy(merged, CombinablePosition) is not None
        assert world.get_copy(merged, PlainTag) is not None
        assert world.get_copy(merged, PlainHealth) is not None

    def test_merge_entities_non_combinable_lww(self) -> None:
        """Non-combinable components use last-writer-wins."""
        world = World()
        e1 = world.spawn(PlainTag("alice"))
        e2 = world.spawn(PlainTag("bob"))

        merged = world.merge_entities(e1, e2)

        tag = world.get_copy(merged, PlainTag)
        assert tag is not None
        assert tag.name == "bob"

    def test_merge_entities_only_one_has_component(self) -> None:
        """Merged entity keeps components that appear on only one source entity."""
        world = World()
        e1 = world.spawn(PlainTag("alice"))
        e2 = world.spawn(PlainHealth(100, ["stable"]))

        merged = world.merge_entities(e1, e2)

        tag = world.get_copy(merged, PlainTag)
        health = world.get_copy(merged, PlainHealth)
        assert tag is not None and tag.name == "alice"
        assert health is not None and health.hp == 100

    def test_merge_entities_nonexistent_raises(self) -> None:
        """Merging nonexistent entity raises ValueError."""
        world = World()
        e1 = world.spawn(CombinablePosition(0, 0))
        world.destroy(e1)

        e2 = world.spawn(CombinablePosition(10, 10))

        with pytest.raises(ValueError, match="does not exist"):
            world.merge_entities(e1, e2)


class TestSplitEntity:
    """Tests for World.split_entity()."""

    def test_split_entity_with_splittable(self) -> None:
        """Splittable components are split via __split__."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity)

        left_credits = world.get_copy(left, SplittableCredits)
        right_credits = world.get_copy(right, SplittableCredits)
        assert left_credits is not None
        assert right_credits is not None
        assert left_credits.amount == pytest.approx(50.0)
        assert right_credits.amount == pytest.approx(50.0)

    def test_split_entity_destroys_original(self) -> None:
        """Original entity is destroyed after split."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))

        left, right = world.split_entity(entity)

        assert world.get_copy(entity, SplittableCredits) is None
        assert world.get_copy(left, SplittableCredits) is not None
        assert world.get_copy(right, SplittableCredits) is not None

    def test_split_entity_non_splittable_deepcopy(self) -> None:
        """Non-splittable components are deep-copied to both entities."""
        world = World()
        entity = world.spawn(PlainHealth(100, ["stable"]))

        left, right = world.split_entity(entity)

        left_health = world.get_copy(left, PlainHealth)
        right_health = world.get_copy(right, PlainHealth)

        assert left_health is not None
        assert right_health is not None
        assert left_health.hp == 100
        assert right_health.hp == 100

        left_raw = world._storage.get_component(left, PlainHealth, copy=False)
        right_raw = world._storage.get_component(right, PlainHealth, copy=False)
        assert left_raw is not None
        assert right_raw is not None
        assert left_raw is not right_raw

    def test_split_entity_non_splittable_independence(self) -> None:
        """Mutating one split copy does not affect the other copy."""
        world = World()
        entity = world.spawn(PlainHealth(100, ["stable"]))

        left, right = world.split_entity(entity)

        left_raw = world._storage.get_component(left, PlainHealth, copy=False)
        right_raw = world._storage.get_component(right, PlainHealth, copy=False)
        assert left_raw is not None
        assert right_raw is not None

        left_raw.notes.append("damaged")
        assert right_raw.notes == ["stable"]

    def test_split_entity_nonexistent_raises(self) -> None:
        """Splitting nonexistent entity raises ValueError."""
        world = World()
        entity = world.spawn(SplittableCredits(100.0))
        world.destroy(entity)

        with pytest.raises(ValueError, match="does not exist"):
            world.split_entity(entity)


class TestMergeSplitRoundtrip:
    """Tests verifying merge and split are compatible."""

    def test_split_then_merge_roundtrip(self) -> None:
        """Split then merge preserves component values for this setup."""
        world = World()
        entity = world.spawn(CombinablePosition(10, 20), SplittableCredits(100.0))

        left, right = world.split_entity(entity)
        merged = world.merge_entities(left, right)

        pos = world.get_copy(merged, CombinablePosition)
        credits = world.get_copy(merged, SplittableCredits)

        assert pos is not None
        assert credits is not None
        assert pos.x == pytest.approx(10.0)
        assert pos.y == pytest.approx(20.0)
        assert credits.amount == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_scoped_access_merge_entities() -> None:
    """ScopedAccess can queue merge operations with provisional IDs."""
    world = World()
    e1 = world.spawn(CombinablePosition(0, 0), PlainTag("alice"))
    e2 = world.spawn(CombinablePosition(10, 20), PlainTag("bob"))

    provisional: EntityId | None = None

    @system(reads=(CombinablePosition, PlainTag), writes=(CombinablePosition, PlainTag))
    def merge_system(access: ScopedAccess) -> None:
        nonlocal provisional
        provisional = access.merge_entities(e1, e2)

    world.register_system(merge_system)
    await world.tick_async()

    assert provisional is not None
    assert provisional.index < 0
    assert world.get_copy(e1, CombinablePosition) is None
    assert world.get_copy(e2, CombinablePosition) is None

    merged_entities = list(world.query_copies(CombinablePosition, PlainTag))
    assert len(merged_entities) == 1

    _, pos, tag = merged_entities[0]
    assert pos.x == pytest.approx(5.0)
    assert pos.y == pytest.approx(10.0)
    assert tag.name == "bob"


@pytest.mark.asyncio
async def test_scoped_access_split_entity() -> None:
    """ScopedAccess can queue split operations with provisional IDs."""
    world = World()
    entity = world.spawn(SplittableCredits(100.0), PlainHealth(100, ["stable"]))

    provisional: tuple[EntityId, EntityId] | None = None

    @system(reads=(SplittableCredits, PlainHealth), writes=(SplittableCredits, PlainHealth))
    def split_system(access: ScopedAccess) -> None:
        nonlocal provisional
        provisional = access.split_entity(entity)

    world.register_system(split_system)
    await world.tick_async()

    assert provisional is not None
    assert provisional[0].index < 0
    assert provisional[1].index < 0
    assert provisional[0] != provisional[1]
    assert world.get_copy(entity, SplittableCredits) is None

    split_entities = list(world.query_copies(SplittableCredits, PlainHealth))
    assert len(split_entities) == 2

    amounts = sorted(credits.amount for _, credits, _ in split_entities)
    assert amounts == [50.0, 50.0]
    assert all(health.hp == 100 for _, _, health in split_entities)
    assert all(health.notes == ["stable"] for _, _, health in split_entities)


@pytest.mark.asyncio
async def test_scoped_access_merge_access_violation() -> None:
    """Missing read access on merge target components raises AccessViolationError."""
    world = World()
    e1 = world.spawn(CombinablePosition(0, 0), PlainTag("alice"))
    e2 = world.spawn(CombinablePosition(10, 20), PlainTag("bob"))

    @system(reads=(CombinablePosition,), writes=(CombinablePosition,))
    def merge_system(access: ScopedAccess) -> None:
        access.merge_entities(e1, e2)

    world.register_system(merge_system)

    with pytest.raises(AccessViolationError, match="cannot read PlainTag"):
        await world.tick_async()
