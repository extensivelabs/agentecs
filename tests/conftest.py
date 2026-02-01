"""Shared test fixtures."""

import sys

import pytest

# Ensure src is in path
sys.path.insert(0, "src")

from dataclasses import dataclass

from agentecs import World, component


@pytest.fixture
def world():
    """Fresh World instance."""
    return World()


@component
@dataclass(slots=True)
class FixturePosition:
    x: float
    y: float


@component
@dataclass(slots=True)
class FixtureVelocity:
    dx: float
    dy: float


@pytest.fixture
def position_cls():
    return FixturePosition


@pytest.fixture
def velocity_cls():
    return FixtureVelocity
