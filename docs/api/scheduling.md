# Scheduling API

Parallel execution engine with conflict detection.

## Overview

The scheduler automatically parallelizes system execution based on declared access patterns:
- **Conflict detection**: Identifies write-write and read-write conflicts
- **Parallel execution**: Groups non-conflicting systems
- **Query optimization**: Leverages query disjointness for more parallelism
- **Async-first**: Uses asyncio.gather for efficient concurrent execution

**Execution Modes:**
- **Parallel**: Default mode, maximizes throughput
- **Sequential**: For debugging and deterministic execution

---

## SimpleScheduler

Parallel execution with conflict detection and query disjointness optimization.

::: agentecs.scheduling.SimpleScheduler
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - schedule
        - tick
        - tick_async

---

## SequentialScheduler

Simple sequential execution for debugging.

::: agentecs.scheduling.SequentialScheduler
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - schedule
        - tick
        - tick_async

---

## Conflict Detection

How the scheduler determines if systems can run in parallel:

### Write-Write Conflicts
Two systems conflict if both write to the same component type.

```python
@system(writes=(Position,))
def move_system(world): ...

@system(writes=(Position,))  # Conflicts with move_system
def teleport_system(world): ...
```

### Read-Write Conflicts
A system reading a component conflicts with one writing it.

```python
@system(reads=(Position,), writes=(Velocity,))
def physics_system(world): ...

@system(writes=(Position,))  # Conflicts with physics_system
def move_system(world): ...
```

### Query Disjointness
Systems with provably disjoint queries can parallelize even with same component types.

```python
@system(reads=Query().having(Agent, Active))
def active_agents(world): ...

@system(reads=Query().having(Agent, Inactive))  # Disjoint!
def inactive_agents(world): ...
```

---

## Usage Example

```python
from agentecs import World
from agentecs.scheduling import SimpleScheduler, SchedulerConfig

# Create world with scheduler
world = World(execution=SimpleScheduler())

# Or with custom config
world = World(
    execution=SimpleScheduler(
        config=SchedulerConfig(
            max_concurrent=10
        )
    )
)

# Register systems
world.register_system(movement_system)
world.register_system(physics_system)
world.register_system(rendering_system)

# Execute one tick (parallel)
await world.tick_async()

# Or synchronous wrapper
world.tick()
```

---

## Future Enhancements

**Frequency-Based Execution** (Planned):
- Systems declare execution frequency (every N ticks)
- Reduces unnecessary computation
- Phase-based grouping

**Context-Aware Scheduling** (Research):
- Optimize for LLM cache hits
- Group systems with overlapping context
- Learn optimal schedules from execution patterns
