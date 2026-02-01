# What is AgentECS and why another agent framework?

AgentECS is a new AI agent framework based on the Entity-Component-System (ECS) architectural pattern.

Existing agent frameworks are largely either monolithic agents interacting through handoffs or graph-based workflows
By contrast, AgentECS decouples AI agents into:

- **Entities** = Agent identities
- **Components** = Agent capabilities and state
- **Systems** = Behaviors that emerge from combinations of components or even agents

This results in features unique to AgentECS:
<div class="grid cards" markdown>


- :material-cogs: **Emergent Workflows**

    No explicit graphs needed, behavior emerges from system and their interactions

- :material-database: **Resource Sharing**

    Agents can share or even compete for resources (LLMs, tasks, context)

- :material-shape-square-plus: **Dynamic Agents**

    Agents can merge, split, spawn or be destroyed

- :material-earth: **Dynamic Environments**

    Environments can change based on the state of the agentic society

- :material-scale-balance: **Dynamic Granularity**

    Systems can operate on any level of granularity, from single agents to entire swarms

- :material-server: **Parallel Execution**

    Automatic parallelization from declared access patterns at any scale


</div>

For instance, check out the following examples where:

- ... workflows emerge from agentic interactions
- ... agents compete for context space
- ... agents merge and split on demand
- ... the environment changes depending on agent's consensus

## Quick Example

```python
from dataclasses import dataclass
from agentecs import World, component, system, ScopedAccess

@component
@dataclass
class Position:
    x: float
    y: float

@component
@dataclass
class Velocity:
    dx: float
    dy: float

@system(reads=(Position, Velocity), writes=(Position,))
def movement(world: ScopedAccess) -> None:
    for entity, pos, vel in world(Position, Velocity):
        world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)

world = World()
# Create an entity with Position and Velocity components
world.spawn(Position(0, 0), Velocity(1, 0))
# Register the movement system
world.register_system(movement)
# Advance the world state by one tick
world.tick()
```

## Why do we need another framework for AI Agents?
There is nothing wrong with either approach. However both make strong assumptions: We know what workflow we need, and we know how agentic interactions should be orchestrated.

We are early in the days of AI agents and there is a large space of possible workflows and interactions yet to be explored.
AgentECS is designed to enable this exploration.

## Core Principles

### Entities are collections of Components

Entities are instances and have a unique identity. Beyond this, they do not contain any behavior themselves.
Instead, they are merely collections of components.

Components are data. For example:
```python

@component
@dataclass
class Position:
    x: float
    y: float

@component
@dataclass
class Velocity:
    dx: float
    dy: float
```

And entities are collections of these components:
```python
entity = world.spawn(Position(0, 0), Velocity(1, 0))
```

That's it. No special entity classes, no behavior attached.

### Systems operate on combinations of Components

Systems operate on combinations of components.
A typical workflow is to query for entities with certain components, read their state, and write new state back.

```python
@system(reads=(Position, Velocity), writes=(Position,))
def movement(world: ScopedAccess) -> None:
    for entity, pos, vel in world(Position, Velocity):
        world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)
```

### The world moves with ticks

The changes made by systems are applied to the world state in discrete ticks. One tick is the smallest unit of change in AgentECS.

```python
world.register_system(movement)
world.tick()  # Advances the world state by one tick
```

Within a tick, systems execute in **groups**. Systems in the same group see a consistent snapshot of the world state. Their changes are merged and applied at the group boundary, before the next group executes.

### Access Patterns Enable Parallelism

Declared reads/writes provide validation and documentation. Systems in the same execution group run in parallel with snapshot isolation:

```python
# These run in parallel - changes merge at group boundary
@system(reads=(Position,), writes=(Position,))
@system(reads=(Health,), writes=(Health,))

# Access declarations are optional - skip for prototyping
@system()  # Full access, still runs in parallel
def prototype(world):
    # Can read/write anything
    pass
```


## Next Steps

- Follow the [Installation Guide](start-up/installation.md) to get started
- Read [Core Concepts](start-up/core-concepts.md) to understand the fundamentals
- Explore the [Cookbook](cookbook/index.md) for practical patterns
- Dive into [System Documentation](system/index.md) for architecture details
