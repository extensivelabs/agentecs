# Storage API

Pluggable storage backend for component data.

## Overview

AgentECS uses a protocol-based storage architecture, allowing different backend implementations:
- **LocalStorage**: In-memory storage for single-process use
- **Future**: Archetypal storage, distributed backends, persistent storage

**Key Features:**
- Protocol-based: Easy to swap implementations
- Generational liveness: Safe entity recycling
- Efficient queries: Filter entities by component types
- Batch operations: Apply multiple updates atomically

---

## Storage Protocol

Interface that all storage backends must implement.

::: agentecs.storage.Storage
    options:
      show_root_heading: true
      show_source: true
      members:
        - create_entity
        - destroy_entity
        - entity_exists
        - get_component
        - set_component
        - remove_component
        - has_component
        - get_component_types
        - query
        - apply_updates
        - snapshot
        - restore

---

## LocalStorage

In-memory implementation for single-process use.

::: agentecs.storage.LocalStorage
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - create_entity
        - destroy_entity
        - entity_exists
        - get_component
        - set_component
        - remove_component
        - has_component
        - get_component_types
        - query
        - apply_updates
        - snapshot
        - restore

---

## Usage Example

```python
from agentecs import World
from agentecs.storage import LocalStorage

# Use default LocalStorage
world = World()

# Or provide custom storage
custom_storage = LocalStorage()
world = World(storage=custom_storage)
```

## Future Storage Backends

**ArchetypalStorage** (Planned):
- Cache-friendly memory layout
- O(matched) query performance
- Optimized for iteration over large entity sets

**Distributed Storage** (Research):
- Cross-shard queries
- Eventual consistency models
- Network-aware optimization
