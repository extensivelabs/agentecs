"""Execution plan construction."""

from __future__ import annotations

from agentecs.models.scheduling import ExecutionGroup, ExecutionPlan
from agentecs.models.system import SystemDescriptor


def build_single_group_plan(systems: list[SystemDescriptor]) -> ExecutionPlan:
    """Default builder: all systems in one group, dev systems isolated.

    Creates two types of groups:
    1. One group per dev system (runs alone, first)
    2. One group for all normal systems (runs in parallel)

    This provides maximum parallelism while respecting dev mode isolation.
    """
    dev_systems: list[SystemDescriptor] = []
    normal_systems: list[SystemDescriptor] = []

    for system in systems:
        if system.is_dev_mode():
            dev_systems.append(system)
        else:
            normal_systems.append(system)

    groups: ExecutionPlan = []

    # Dev systems each get their own group (run sequentially, alone)
    for dev_system in dev_systems:
        groups.append(ExecutionGroup(systems=[dev_system]))

    # All normal systems in one group (run in parallel)
    if normal_systems:
        groups.append(ExecutionGroup(systems=normal_systems))

    return groups
