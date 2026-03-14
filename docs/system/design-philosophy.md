# Design Philosophy

AgentECS applies the Entity-Component-System (ECS) paradigm to AI agent orchestration, emphasizing two key principles:

1. **Composition** - Agents are composed of modular components that define their data and capabilities
2. **System-Driven Behavior** - Behaviors emerge from systems operating on component patterns

This architecture enables emergent workflows, where complex agent behaviors arise from the interaction of simple systems and components, rather than being explicitly defined.

## Why AgentECS for AI Agents?

Existing agent frameworks are largely either:

- **Bundled agents** interacting through handoffs
- **Graph-based workflows** connecting agentic actions

Both approaches make strong assumptions: we know what workflow we need, and we know how it should be orchestrated.

By contrast, AgentECS assumes we're in the early days of AI agent development. We don't yet know the best patterns, and premature optimization toward specific workflows may limit exploration.

**What AgentECS Enables:**

1. **Flexibility** - No rigid workflow graphs or agent hierarchies
2. **Scalability** - From single agents to massive swarms
3. **Emergent Workflows** - Behavior emerges from system interactions
4. **Resource Sharing** - Agents can share or compete for resources (LLMs, context)
5. **Parallel Execution** - Automatic parallelization with snapshot isolation

## Core Architectural Principles

### Flexibility Over Enforcement

AgentECS prioritizes flexibility and rapid prototyping. Access declarations, type constraints, and validation are **optional**—use them when they help, skip them when they don't.

**Why Optional:**
- Early-stage AI agent research requires experimentation
- Different use cases need different levels of structure
- Add rigor incrementally as patterns stabilize

### Merge Over Prevention

Instead of preventing conflicts through scheduling constraints, AgentECS **embraces conflicts** and resolves them during deterministic application.

Systems run in parallel, writing to isolated buffers. At group boundaries, results are applied in registration order:
- `Combinable` values fold via `__combine__`
- non-combinable values use last-writer-wins

**Why Merge-Based:**
- Enables parallelism without rigid dependency graphs
- Semantic combination through component protocols preserves intent
- Supports distributed execution across nodes
- Reflects real-world agent coordination

### Snapshot Isolation with Execution Groups

Systems execute in **groups**. Within a group:
- All systems see the same initial state (snapshot)
- Systems run in parallel (respecting concurrency limits)
- Results merge at group boundary
- Next group sees merged changes

**Why Groups:**
- Safe parallelism without race conditions
- Reasoning is local to a group, not global tick
- Supports batch operations and optimizations

### Buffered Writes

Systems write to a buffer, not directly to storage. Changes are:
- Immediately visible to the writing system (read-your-writes)
- Invisible to other systems in the same group
- Applied atomically at group boundaries

**Why Buffering:**
- Snapshot isolation (predictable system behavior)
- Safe parallelization (no shared mutable state)
- Testable systems (pure functions with explicit outputs)

### Pluggable Storage and Scheduling

Storage and execution are **protocols**, not implementations. Swap backends without changing logic.

**Why Pluggable:**
- Different workloads need different backends
- Testing with mocks (no real database/API)
- Gradual migration (prototype → production)

### Optional Component Protocols

Components are plain dataclasses. Advanced features are **opt-in** through runtime-checkable protocols:

- `Combinable`: Combine component values
- `Splittable`: Divide component between entities

**Why Optional:**
- Simple components stay simple (just data)
- Add operations only when needed
- Fallback strategies for components without protocols

### No Special Resources

Global state, shared resources, and configuration are **components on singleton entities**, not special framework constructs.

**Why Singletons as Components:**
- Consistent API (all state is components)
- Systems declare access to singletons like any component
- No special "resource" or "config" abstractions
- Serializable world state

### Generational Entity IDs

Entities use **generational indices** to prevent stale references. Each EntityId contains a shard (for distribution), index (unique within shard), and generation (incremented on reuse).

**Why Generations:**
- Entity IDs can be recycled without confusion
- Old references fail safely (generation mismatch)
- Supports distributed allocation
- Memory efficient

### Async-First Design

Systems can be sync or async. Framework handles both seamlessly, detecting via inspection.

**Why Async-First:**
- AI agents are I/O-bound (LLM calls, database queries)
- Maximize throughput with concurrent operations
- Mix sync and async systems freely

### Dev Mode for Debugging

Systems can run in **dev mode** for easier debugging: they run in isolation, have full access without declarations, and execute before normal systems.

**Why Dev Mode:**
- Simpler reasoning (no parallel interference)
- Full access without declarations
- Temporary debugging without changing architecture

## Design Trade-offs

### Flexibility vs Structure

**Trade-off:** Optional access declarations mean less compile-time safety.

**Rationale:** Early AI agent research needs experimentation. Add structure incrementally as patterns emerge.

### Merge vs Determinism

**Trade-off:** Application ordering can produce different results than sequential execution.

**Rationale:** Parallelism is essential for scalability. Semantic combination (via `__combine__`) preserves intent better than forced sequencing.

### Simplicity vs Optimization

**Trade-off:** Initial storage implementation prioritizes simplicity over performance.

**Rationale:** Start simple, profile, optimize when needed. Premature optimization increases complexity without proven benefit.

### Protocols vs Base Classes

**Trade-off:** Runtime protocol checking is slower than inheritance.

**Rationale:** Protocols are non-invasive (components stay plain dataclasses). Runtime check overhead is negligible compared to LLM calls in agent workloads.

## See Also

- **[Architecture](architecture.md)**: Overall system architecture
- **[Systems](systems.md)**: How systems implement these principles
- **[Components](components.md)**: Component protocols in detail
- **[Scheduling](scheduling.md)**: Execution groups and result combination
- **[World Management](world_management.md)**: Entity lifecycle and operations
