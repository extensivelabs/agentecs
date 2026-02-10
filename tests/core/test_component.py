"""Tests for component system."""

from dataclasses import dataclass
from unittest.mock import patch

import pytest

from agentecs import component, merge_components, reduce_components
from agentecs.core.component import ComponentRegistry


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


def test_merge_with_mergeable_protocol():
    """merge_components uses __merge__ if available."""

    @component
    @dataclass
    class MergeableComp:
        value: int

        def __merge__(self, other: "MergeableComp") -> "MergeableComp":
            return MergeableComp(self.value + other.value)

    comp1 = MergeableComp(10)
    comp2 = MergeableComp(20)

    result = merge_components(comp1, comp2)

    assert result.value == 30


def test_merge_without_mergeable_raises():
    """merge_components raises if component doesn't implement Mergeable."""

    @component
    @dataclass
    class NonMergeableComp:
        value: int

    comp1 = NonMergeableComp(10)
    comp2 = NonMergeableComp(20)

    with pytest.raises(TypeError, match="not Mergeable"):
        merge_components(comp1, comp2)


def test_merge_with_strategy():
    """merge_components uses custom strategy if provided."""

    @component
    @dataclass
    class StrategyComp:
        value: int

    comp1 = StrategyComp(10)
    comp2 = StrategyComp(20)

    def max_strategy(a: StrategyComp, b: StrategyComp) -> StrategyComp:
        return StrategyComp(max(a.value, b.value))

    result = merge_components(comp1, comp2, strategy=max_strategy)

    assert result.value == 20


def test_reduce_components_with_reduce_many():
    """reduce_components uses __reduce_many__ if available."""

    @component
    @dataclass
    class ReducibleComp:
        value: int

        @classmethod
        def __reduce_many__(cls, items: list["ReducibleComp"]) -> "ReducibleComp":
            return ReducibleComp(sum(c.value for c in items))

    comps = [ReducibleComp(10), ReducibleComp(20), ReducibleComp(30)]

    result = reduce_components(comps)

    assert result.value == 60


def test_reduce_components_fallback_to_merge():
    """reduce_components falls back to sequential merge."""

    @component
    @dataclass
    class SeqMergeComp:
        value: int

        def __merge__(self, other: "SeqMergeComp") -> "SeqMergeComp":
            return SeqMergeComp(self.value + other.value)

    comps = [SeqMergeComp(1), SeqMergeComp(2), SeqMergeComp(3)]

    result = reduce_components(comps)

    assert result.value == 6  # 1+2+3


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
