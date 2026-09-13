"""Public entry points: the decorators and the pre-wired World."""

from agentecs.api.decorators import component, system
from agentecs.api.world import World

__all__ = [
    "World",
    "component",
    "system",
]
