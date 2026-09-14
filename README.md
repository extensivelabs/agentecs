# AgentECS

[![CI](https://github.com/extensivelabs/agentecs/actions/workflows/ci.yml/badge.svg)](https://github.com/extensivelabs/agentecs/actions/workflows/ci.yml)
[![Documentation](https://github.com/extensivelabs/agentecs/actions/workflows/docs.yml/badge.svg)](https://extensivelabs.github.io/agentecs)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/extensivelabs/agentecs)](LICENSE)

**Entity Component System for AI Agent Orchestration**

## Core Idea

AgentECS applies the ECS (Entity-Component-System) paradigm to AI agent orchestration. Unlike traditional agent frameworks that bundle functionality into monolithic agent classes or use explicit graph-based workflows, AgentECS decouples:

- **Entities** = Agent identities (lightweight IDs)
- **Components** = Agent capabilities and state (pure data)
- **Systems** = Behaviors that emerge from component combinations

This enables:
- Systems executing based on groupings of comonents rather than individual agents
- Agents sharing resources (LLMs, context) without hard coupling
- Emergent workflows without explicit dependency graphs
- Parallel execution via declared access patterns
- Dynamic agent merging/splitting at runtime

## Documentation

📚 **[Read the full documentation](https://extensivelabs.github.io/agentecs)**

- [Getting Started](https://extensivelabs.github.io/agentecs/start-up/installation/)
- [Cookbook](https://extensivelabs.github.io/agentecs/cookbook/)
- [System Documentation](https://extensivelabs.github.io/agentecs/system/)
- [Architecture Deep Dive](https://extensivelabs.github.io/agentecs/architecture/) — internals, call stacks, known gaps
- [API Reference](https://extensivelabs.github.io/agentecs/api/)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AgentECS                                │
├─────────────────────────────────────────────────────────────────┤
│  ENTITIES                                                       │
│  └── EntityId(shard, index, generation)                         │
│      Lightweight IDs with generation for safe recycling         │
│      Shard field enables future distributed scaling             │
├─────────────────────────────────────────────────────────────────┤
│  COMPONENTS (@component decorator)                              │
│  └── Pure data: dataclass or Pydantic models                    │
│      Optional protocols: Mergeable, Splittable, Diffable        │
│      Deterministic IDs from class name (safe across nodes)      │
├─────────────────────────────────────────────────────────────────┤
│  SYSTEMS (@system decorator with access declarations)           │
│  └── Pure functions: (ScopedAccess) -> SystemResult | None      │
│      Tiered access: dev mode | type-level | query-level         │
│      Behaviour emerges from declarations, no explicit graphs    │
├─────────────────────────────────────────────────────────────────┤
│  WORLD                                                          │
│  └── ScopedAccess: Rust-like read/write enforcement             │
│      Write buffer: snapshot isolation (read own writes)         │
│      Magic methods: world[e, T], world(T1, T2), (e, T) in world │
├─────────────────────────────────────────────────────────────────┤
│  SCHEDULER                                                      │
│  └── Builds an execution plan: an ordered list of groups        │
│      Parallel within a group, groups applied in sequence        │
│      Write conflicts resolve at apply time (__combine__ / LWW)  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

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

## Development

### AI Usage

Different from associated repos (such as agentecs-viz), AI use in this repo is contained to:

- documentation
- project management (issues, PRs, project board)
- code review
- chores
- some test writing

To ensure the framework is as sound as can be, actual code is written by humans.
Artisanal and all that.

### Development Setup

This project supports [direnv](https://direnv.net/) for automatic environment management:

```bash
# Install direnv and configure your shell (one-time)
# See: https://direnv.net/docs/installation.html

# Trust the .envrc file (one-time per clone)
direnv allow

# Environment auto-loads when you cd into the project
# - Activates .venv
# - Loads .env (API keys, config)
# - Sets PYTHONPATH
```

Without direnv, manually activate: `source .venv/bin/activate`

For detailed setup instructions, see the [Getting Started guide](https://extensivelabs.github.io/agentecs/start-up/installation/).
## Future Work

- **Distributed scaling**: Sharded storage, cross-node queries
- **Rust backend**: PyO3 bindings for storage and query engine
- **External adapters**: MCP, A2A protocol support
- **Research features**: Agent merging/splitting, contested resources, topology systems
