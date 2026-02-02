# AgentECS

**Entity Component System for AI Agent Orchestration**

AgentECS applies the ECS architectural pattern to AI agents, enabling flexible, scalable, and emergent agent workflows.

<div class="grid cards" markdown>

- :material-arrow-right-box: **[Getting Started](start-up/installation.md)**

    Install AgentECS and run your first system

- :material-book-open-variant: **[Core Concepts](start-up/core-concepts.md)**

    Understand entities, components, and systems

- :material-chef-hat: **[Cookbook](cookbook/index.md)**

    Practical examples and patterns

- :material-file-document: **[API Reference](api/index.md)**

    Complete API documentation

</div>

---

## Why Another Agent Framework?

Existing frameworks assume we know what agentic workflows should look like:

- **Monolithic agents** with hand-off protocols
- **Graph-based workflows** with explicit orchestration

We're early in AI agents. The design space is vast and largely unexplored.

AgentECS takes a different approach. Decouple agents into primitives:

- **Entities** = Identities (agents, tasks, resources)
- **Components** = Data (state, capabilities, context)
- **Systems** = Behavior (operates on component patterns)

Then let workflows **emerge** from their interactions.

<div class="grid cards" markdown>

- :material-cogs: **Emergent Workflows**

    No explicit graphs needed. Behavior emerges from system interactions.

- :material-share-variant: **Resource Sharing**

    Agents can share or compete for resources: LLMs, context, tasks.

- :material-call-split: **Dynamic Agents**

    Agents can merge, split, spawn, or be destroyed at runtime.

- :material-earth: **Dynamic Environments**

    The environment can change based on collective agent state.

- :material-resize: **Flexible Granularity**

    Systems operate on any level: single agents, groups, or entire swarms.

- :material-server: **Automatic Parallelism**

    Declared access patterns enable safe parallel execution at scale.

</div>

---

## Quick Example

```python
from dataclasses import dataclass
from agentecs import World, component, system, ScopedAccess

@component
@dataclass
class Agent:
    name: str

@component
@dataclass
class Task:
    description: str
    done: bool = False

@system(reads=(Agent, Task), writes=(Task,))
def work(world: ScopedAccess) -> None:
    for entity, agent, task in world(Agent, Task):
        if not task.done:
            print(f"{agent.name}: {task.description}")
            world[entity, Task] = Task(task.description, done=True)

# Create world and register system
world = World()
world.register_system(work)

# Spawn agents with tasks
world.spawn(Agent("Alice"), Task("Write report"))
world.spawn(Agent("Bob"), Task("Review code"))

# Run one tick - both agents work in parallel
world.tick()
```

Output:
```
Alice: Write report
Bob: Review code
```

---

## Core Principles

### Entities Are Just IDs

Entities have no behavior. They're identities that hold components together:

```python
# An agent is just an entity with certain components
agent = world.spawn(
    Agent(name="Alice"),
    Context(messages=[]),
    Task(description="Analyze data"),
)
```

### Systems Operate on Patterns

Systems query for component combinations, not specific entities:

```python
@system(reads=(Agent, Task), writes=(Task,))
def work(world: ScopedAccess) -> None:
    # Finds ALL entities with both Agent AND Task
    for entity, agent, task in world(Agent, Task):
        ...
```

### Changes Apply at Tick Boundaries

Systems write to a buffer. Changes merge and apply when the tick completes:

```python
world[entity, Task] = Task(...)  # Buffered, not immediate
world.tick()                      # All changes apply atomically
```

This enables snapshot isolation: systems see consistent state, even when running in parallel.

### Access Patterns Enable Parallelism

Declare what components a system reads and writes. Non-conflicting systems run in parallel:

```python
# These CAN run in parallel (disjoint writes)
@system(reads=(Position,), writes=(Position,))
@system(reads=(Health,), writes=(Health,))

# These CANNOT (both write Position)
@system(reads=(Position,), writes=(Position,))
@system(reads=(Velocity,), writes=(Position,))
```

---

## What Can You Build?

AgentECS enables workflows that are awkward or impossible in traditional frameworks:

- **Agent swarms** that scale to thousands of concurrent agents
- **Competitive agents** fighting for shared context or resources
- **Social dynamics** where agents merge based on similarity
- **Hierarchical agents** that split tasks and spawn sub-agents
- **Adaptive environments** that respond to collective agent behavior
- **Monte Carlo search** with parallel simulation branches

---

## Next Steps

- **[Installation](start-up/installation.md)** - Get AgentECS running
- **[Core Concepts](start-up/core-concepts.md)** - Understand the fundamentals
- **[Cookbook](cookbook/index.md)** - Learn common patterns
- **[Architecture](system/index.md)** - Deep dive into internals
