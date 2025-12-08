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
- Agents sharing resources (LLMs, context) without hard coupling
- Emergent workflows without explicit dependency graphs
- Parallel execution via declared access patterns
- Dynamic agent merging/splitting at runtime

## Documentation

📚 **[Read the full documentation](https://extensivelabs.github.io/agentecs)**

- [Getting Started](https://extensivelabs.github.io/agentecs/start-up/installation/)
- [Cookbook](https://extensivelabs.github.io/agentecs/cookbook/)
- [System Documentation](https://extensivelabs.github.io/agentecs/system/)
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
│      Frequency-based scheduling, no explicit graphs             │
├─────────────────────────────────────────────────────────────────┤
│  WORLD                                                          │
│  └── ScopedAccess: Rust-like read/write enforcement             │
│      Write buffer: snapshot isolation (read own writes)         │
│      Magic methods: world[e, T], world(T1, T2), (e, T) in world │
├─────────────────────────────────────────────────────────────────┤
│  SCHEDULER                                                      │
│  └── Analyzes access patterns for automatic parallelization     │
│      Detects conflicts, groups non-conflicting systems          │
│      Sequential within groups, parallel across groups           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Components are Copies - Must Write Back

**All reads return copies.** Mutate freely, but must write back:

```python
@system(reads=(Position, Velocity), writes=(Position,))
def movement(world: ScopedAccess) -> None:
    for entity, pos, vel in world(Position, Velocity):
        # pos and vel are COPIES - mutations won't persist
        # Create new instance and write back:
        world[entity, Position] = Position(pos.x + vel.dx, pos.y + vel.dy)

        # Alternative: mutate copy then write back:
        # pos.x += vel.dx
        # pos.y += vel.dy
        # world[entity, Position] = pos  # Write required!
```

Writes go to a buffer, enabling:
- Snapshot isolation (consistent state per system)
- Safe parallelization (no shared mutable state)
- Read-own-writes within the same system

### 2. Access Patterns Enable Parallelism

Declared reads/writes allow the scheduler to detect conflicts:

```python
# These CAN run in parallel (disjoint write sets)
@system(reads=(Position,), writes=(Position,))  # writes Position
@system(reads=(Health,), writes=(Health,))      # writes Health

# These CANNOT (conflicting access)
@system(reads=(Position,), writes=(Position,))  # writes Position
@system(reads=(Position,), writes=(Velocity,))  # reads Position
```

### 3. No Special "Resources" - Just Singleton Components

LLM access, configuration, and other global state are components on a well-known entity:

```python
world.set_singleton(LLMConfig(model="claude", temperature=0.7))

# In system:
config = world.singleton(LLMConfig)
```

### 4. Component Operations are Optional Protocols

Components CAN implement merge/split/diff, but don't have to:

```python
@component
@dataclass
class Context:
    history: list[str]

    def __merge__(self, other: "Context") -> "Context":
        return Context(history=self.history + other.history)
```

## Development Setup

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

## Quick Start

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
agent = world.spawn(Position(0, 0), Velocity(1, 0))
world.register_system(movement)
world.tick()
```

## Future Work

- **Distributed scaling**: Sharded storage, cross-node queries
- **Rust backend**: PyO3 bindings for storage and query engine
- **External adapters**: MCP, A2A protocol support
- **Research features**: Agent merging/splitting, contested resources, topology systems
