# AgentECS Documentation

**Entity Component System for AI Agent Orchestration**

Welcome to the AgentECS documentation. AgentECS applies the ECS paradigm to AI agent orchestration, enabling flexible, scalable, and emergent agent workflows.

## Quick Links

- **[Getting Started](start-up/installation.md)** - Install and run your first AgentECS system
- **[Cookbook](cookbook/index.md)** - Practical examples and patterns
- **[System Documentation](system/index.md)** - Architecture and design deep-dives
- **[API Reference](api/index.md)** - Complete API documentation

## What is AgentECS and why another agent framework?

Existing agent frameworks are largely either

- Monolithic agents interacting through handoffs
- Graph-based Workflows, connecting agentic actions

By contrast, AgentECS decouples AI agents into:

- **Entities** = Agent identities
- **Components** = Agent capabilities and state
- **Systems** = Behaviors that emerge from combinations of components or even agents

With the greatest flexibility in what these classes comprise.

Basically, we believe that we are early in the days of AI agents, and that we need to explore a larger space of agentic workflows.

AgentECS is designed to enable this exploration.

For instance, check out the following examples where:

- ... workflows emerge from agentic interactions
- ... agents compete for context space
- ... agents merge based on social proximity
- ... agents that split in response to modular tasks
- ... a Monte-Carlo-Tree-Search agent swarm, parallelizing simulations and discovery
- ... the environment changes depending on agent's consensus

## Features

As ECS, AgentECS inherits many benefits of the paradigm such as flexibility, scalability, and parallelism.
However, we find that when applied to AI agents, new possibilities arise, such as these features:

- **New Systems** - AgentECS enables a strictly larger set of agentic workflows, many we never tried before
- **Emergent Workflows** - No explicit graphs needed, behavior emerges from system and their interactions
- **Resource Sharing** - Agents can share or even compete for resources (LLMs, context)
- **Dynamic Agents** - Agents can merge, split, spawn or be destroyed
- **Parallel Execution** - Automatic parallelization from declared access patterns at any scale
- **Dynamic Environments** - Environments and interactions can depend on actions of agents
- **bAttEriEs iNcluDed** - Of course AgentECS comes with components and systems you can use out-of-the-box

1. **Flexibility** - AgentECS allows flexible workflows and freedom in what elements they comprise
2. **Scalability** - Support for swarms and large-scale workflows without scale boundaries
3. **Emergent Execution** - Automatic scheduling of actions based on access patterns, timings or dependencies
4. **Systems over agents** -


## Core Principles

### Flexibility and systems over agents

While an opinionated framework with a rich class-hierarchy has many advantages, this is only true so long as it fits your use-case. And who knows what the future holds for AI?

AgentECS is flexible.
What is an agent? Well, it's an entity associated with a set of components.

What is a component? It's any data structure you need.

What is a system? It's any transformation of any combination of components.

So, we think in terms of systems, literally.

This means: the level of analysis is flexible. You can absolutely focus on a specific agent, but you can also act on a group, archetypes or patterns of agents.

It also means that AgentECS is lightweight.

### Emergence and Parallelism

By default, you do not need to orchestrate workflows. AgentECS works in ticks, within which systems are scheduled in parallel so long as they do not conflict. Per default, this occurs via access patterns:

```python
# These CAN run in parallel (disjoint write sets)
@system(reads=(Position,), writes=(Position,))
@system(reads=(Health,), writes=(Health,))

# These CANNOT (conflicting access)
@system(reads=(Position,), writes=(Position,))
@system(reads=(Position,), writes=(Velocity,))
```

As such, complex workflows can emerge from simple systems.
Still, you can also encode explicit dependencies or ordering if you want to.

### Systems Return Intent, Don't Mutate

Systems write to a buffer, enabling snapshot isolation and safe parallelization:

```python
@system(reads=(Position, Velocity), writes=(Position,))
def movement(world: ScopedAccess) -> None:
    for entity, pos, vel in world(Position, Velocity):
        world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)
```

## Quick Example

```python
from dataclasses import dataclass, field
from enum import Enum

from agentecs import ScopedAccess, World, component, system


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass
class Task:
    description: str
    status: TaskStatus = TaskStatus.PENDING


@component
@dataclass
class TaskList:
    tasks: list[Task] = field(default_factory=list)


@system(reads=(TaskList,), writes=(TaskList,))
def spawn_agents(world: ScopedAccess) -> None:
    """Spawn agents when pending tasks exceed agent count."""
    agents = list(world(TaskList))
    if not agents:
        return

    _, task_list = agents[0]
    pending = sum(1 for t in task_list.tasks if t.status == TaskStatus.PENDING)

    if pending > len(agents):
        world.spawn(task_list)


@system(reads=(TaskList,), writes=(TaskList,))
def process_tasks(world: ScopedAccess) -> None:
    """Each agent completes one pending task.

    This simulates agents working in parallel on a shared task list.
    """
    for entity, task_list in world(TaskList):
        for task in task_list.tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.COMPLETED
                print(f"Agent {entity.index}: {task.description}")
                world[entity, TaskList] = task_list
                break


world = World()
world.register_system(spawn_agents)
world.register_system(process_tasks)

# Adds 4 tasks to be processed
tasks = TaskList(tasks=[Task(f"Task-{i}") for i in range(1, 5)])
# Adds a single agent with the task list
world.spawn(tasks)
# First tick: Agent works on one task while a new agent is spawned
world.tick()
# Subsequent ticks: Agents process tasks
world.ticket() # ...
```

## Next Steps

- Follow the [Installation Guide](start-up/installation.md) to get started
- Read [Core Concepts](start-up/core-concepts.md) to understand the fundamentals
- Explore the [Cookbook](cookbook/index.md) for practical patterns
- Dive into [System Documentation](system/index.md) for architecture details
