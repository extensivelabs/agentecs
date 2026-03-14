"""Tests for component system."""

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from agentecs import component
from agentecs.core.component import (
    ComponentRegistry,
    combine_protocol_or_fallback,
    reduce_components,
    split_protocol_or_fallback,
)


@pytest.fixture
def registry():
    """Create a ComponentRegistry for testing."""
    return ComponentRegistry()


def test_same_class_produces_same_id(registry):
    """CRITICAL: Same class always gets same component ID.

    Why: Distributed nodes must agree on component IDs for data exchange.
    """

    @component
    @dataclass
    class TestComp:
        value: int

    # Register multiple times
    meta1 = registry.register(TestComp)
    meta2 = registry.register(TestComp)
    meta3 = registry.register(TestComp)

    assert meta1.component_type_id == meta2.component_type_id == meta3.component_type_id


def test_id_stable_across_registry_instances():
    """Component ID is based on class name, not registry instance.

    Why: Different processes create different registries but must agree on IDs.
    """

    @component
    @dataclass
    class StableComp:
        x: int

    registry1 = ComponentRegistry()
    registry2 = ComponentRegistry()

    meta1 = registry1.register(StableComp)
    meta2 = registry2.register(StableComp)

    assert meta1.component_type_id == meta2.component_type_id


def test_different_classes_get_different_ids(registry):
    """Different classes must have different IDs."""

    @component
    @dataclass
    class CompA:
        value: int

    @component
    @dataclass
    class CompB:
        value: int

    meta_a = registry.register(CompA)
    meta_b = registry.register(CompB)

    assert meta_a.component_type_id != meta_b.component_type_id


def test_collision_detection(registry):
    """CRITICAL: Registry detects ID collisions (however unlikely).

    Why: Silent collision = data corruption. Must fail loudly.
    """

    @component
    @dataclass
    class CompA:
        value: int

    @component
    @dataclass
    class CompB:
        value: int

    # Register CompA
    registry.register(CompA)

    # Mock hash collision
    with patch("agentecs.core.component.core._stable_component_type_id") as mock_hash:
        # Make CompB hash to same ID as CompA
        mock_hash.return_value = registry.get_meta(CompA).component_type_id  # type: ignore

        with pytest.raises(RuntimeError, match="Component ID collision"):
            registry.register(CompB)


def test_component_requires_dataclass():
    """Component decorator requires @dataclass or Pydantic model."""
    with pytest.raises(TypeError, match="must be a dataclass"):

        @component
        class NotADataclass:  # Missing @dataclass!
            value: int


def test_combine_protocol_or_fallback_with_combinable():
    """combine_protocol_or_fallback uses __combine__ when available."""
    calls: list[tuple[int, int]] = []

    @component
    @dataclass
    class CombinableComp:
        value: int

        def __combine__(self, other: "CombinableComp") -> "CombinableComp":
            calls.append((self.value, other.value))
            return CombinableComp(self.value + other.value)

    comp1 = CombinableComp(10)
    comp2 = CombinableComp(20)

    result = combine_protocol_or_fallback(comp1, comp2)

    assert calls == [(10, 20)]
    assert result.value == 30


def test_combine_protocol_or_fallback_without_combinable():
    """combine_protocol_or_fallback falls back to second component."""

    @component
    @dataclass
    class PlainComp:
        value: int

    comp1 = PlainComp(10)
    comp2 = PlainComp(20)

    result = combine_protocol_or_fallback(comp1, comp2)

    assert result is comp2


def test_split_protocol_or_fallback_with_splittable():
    """split_protocol_or_fallback uses __split__ when available."""
    calls: list[int] = []

    @component
    @dataclass
    class SplitComp:
        value: int

        def __split__(self) -> tuple["SplitComp", "SplitComp"]:
            calls.append(self.value)
            return (SplitComp(self.value // 2), SplitComp(self.value - (self.value // 2)))

    comp = SplitComp(7)

    left, right = split_protocol_or_fallback(comp)

    assert calls == [7]
    assert left.value == 3
    assert right.value == 4


def test_split_protocol_or_fallback_without_splittable():
    """split_protocol_or_fallback returns two independent deep copies."""

    @component
    @dataclass
    class PlainSplitComp:
        values: list[int] = field(default_factory=list)

    comp = PlainSplitComp([1, 2])

    left, right = split_protocol_or_fallback(comp)

    assert left == comp
    assert right == comp
    assert left is not comp
    assert right is not comp
    assert left is not right

    left.values.append(3)
    assert comp.values == [1, 2]
    assert right.values == [1, 2]


def test_reduce_components_with_combinable_folding():
    """reduce_components folds values by sequential __combine__ calls."""
    calls: list[tuple[str, str]] = []

    @component
    @dataclass
    class FoldComp:
        value: str

        def __combine__(self, other: "FoldComp") -> "FoldComp":
            calls.append((self.value, other.value))
            return FoldComp(f"{self.value}>{other.value}")

    comps = [FoldComp("a"), FoldComp("b"), FoldComp("c")]

    result = reduce_components(comps)

    assert result.value == "a>b>c"
    assert calls == [("a", "b"), ("a>b", "c")]


def test_reduce_components_fallback_to_last_writer_wins():
    """reduce_components returns the last value for non-combinables."""

    @component
    @dataclass
    class PlainReduceComp:
        value: int

    comps = [PlainReduceComp(1), PlainReduceComp(2), PlainReduceComp(3)]

    result = reduce_components(comps)

    assert result is comps[-1]


def test_reduce_empty_list_raises():
    """reduce_components on empty list raises ValueError."""
    with pytest.raises(ValueError, match="Cannot reduce empty list"):
        reduce_components([])


def test_reduce_single_item_returns_item():
    """reduce_components with single item returns that item."""

    @component
    @dataclass
    class SingleComp:
        value: int

    comp = SingleComp(42)
    result = reduce_components([comp])

    assert result is comp
