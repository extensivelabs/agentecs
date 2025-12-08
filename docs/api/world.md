# World API

Central coordination service for entity lifecycle and system execution.

## Overview

The World is the main entry point for AgentECS. It coordinates:
- **Entity lifecycle**: Spawn, destroy, and query entities
- **Component management**: Get, set, and query components
- **System execution**: Register and execute systems with proper isolation
- **Entity operations**: Merge and split entities dynamically

**Key Features:**
- Snapshot isolation: Systems see their own writes immediately
- Atomic updates: Changes applied at tick boundaries
- Parallel execution: Non-conflicting systems run concurrently

---

## World Class

The central coordinator for your ECS world.

::: agentecs.world.World
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - spawn
        - destroy
        - get
        - set
        - has
        - singleton
        - set_singleton
        - merge_entities
        - split_entity
        - register_system
        - execute_system
        - execute_system_async
        - tick
        - tick_async
        - apply_result

---

## Access Control

Systems access the world through scoped interfaces that enforce access patterns.

### ScopedAccess

::: agentecs.world.ScopedAccess
    options:
      show_root_heading: true
      show_source: true
      members:
        - __getitem__
        - __setitem__
        - __delitem__
        - __contains__
        - __call__
        - spawn
        - destroy

### ReadOnlyAccess

::: agentecs.world.ReadOnlyAccess
    options:
      show_root_heading: true
      show_source: true

### EntityHandle

Convenient wrapper for single-entity operations.

::: agentecs.world.EntityHandle
    options:
      show_root_heading: true
      show_source: true
      members:
        - get
        - set
        - has
        - remove

---

## System Results

Systems can return results describing changes to apply.

::: agentecs.world.SystemResult
    options:
      show_root_heading: true
      show_source: true

::: agentecs.world.normalize_result
    options:
      show_root_heading: true
      show_source: true

---

## Entity Allocator

Manages entity ID allocation with generational indices.

::: agentecs.world.EntityAllocator
    options:
      show_root_heading: true
      show_source: true
      members:
        - allocate
        - deallocate
        - is_alive
