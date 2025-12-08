"""Example component implementations demonstrating AgentECS features."""

from dataclasses import dataclass

from agentecs import component


@component
@dataclass(slots=True)
class Position:
    """Example: basic component with interpolation support."""

    x: float
    y: float

    def __merge__(self, other: "Position") -> "Position":
        return Position(x=(self.x + other.x) / 2, y=(self.y + other.y) / 2)

    def __interpolate__(self, other: "Position", t: float) -> "Position":
        return Position(
            x=self.x + (other.x - self.x) * t,
            y=self.y + (other.y - self.y) * t,
        )


@component
@dataclass(slots=True)
class Velocity:
    """Example: simple component, no merge semantics."""

    dx: float
    dy: float


# TODO: Implement example SharedContext with Mergeable, Splittable, Diffable
# TODO: Implement example BeliefState with Diffable for sync
