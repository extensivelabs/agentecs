# Architecture

This page is the conceptual overview. For the implementation — package layers,
annotated call stacks, and the gap between what the API declares and what the
runtime does — see the [Architecture Deep Dive](../architecture/index.md).

## Basic Concepts

When setting up your AgentECS-based application, you will work with three primary concepts: Entities, Components, and Systems.

### Entities

Entities represent unique instances, say an agent. Next to their unique identity, entities are collections of components.
They do not contain any behavior themselves.
More than that, the components are not part of the entity, but merely associated with it in the world state.

Entity identity is covered in [Core Concepts](../start-up/core-concepts.md) and, at
implementation level, in [Altitudes](../architecture/altitudes.md#modelsidentitypy-what-an-entity-is).

### Components

Components are plain data structures that hold the state. An entity can have zero or more components associated with it.
The combination of components defines the capabilities and characteristics of an entity.
For example, an agent entity might have components like Tasks, Memory, and LLMConfig.

Some entities share combinations of components. In this case, we call this type of entity an **archetype**.
However, archetypes are not first-class citizens in the architecture, but merely an optimization for storage and querying.

Learn more about [Components](components.md).

### Systems

Systems encapsulate the logic and behavior that operate on combinations of components - for entities, or across multiple entities.
This point is crucial: Systems are not bound to a specific unit of operation (like an entity), but can operate on any level of granularity.
For example, a system might process all agents with a Tasks component, or it might coordinate between multiple agents to achieve a shared goal.

Learn more about [Systems](systems.md).

## World State and Ticks

The world state is the central repository that holds references to all entities and their associated components.
Systems interact with the world state to read and write component data. As such, the world state handles the effects of systems in discrete ticks.

Each tick represents a snapshot of the world state at a specific point in time. It is the smallest unit of change in AgentECS.
During a tick, systems are executed, and their changes to the world state are applied at the end of the tick.

Systems do not need to run every tick; they can be scheduled to run at specific intervals or based on certain conditions.

## World Access

Systems access the world state through a controlled interface that ensures consistency and isolation.
When a system runs, it receives a scoped view of the world state that includes only the components it has declared access to.
This scoped access allows systems to read and write component data without directly mutating the world state, enabling safe parallel execution and snapshot isolation.

## Scheduling and Parallelism

Systems declare their needs in terms of:

- **Reads** - Components that the system needs to read.
- **Writes** - Components that the system needs to write.

The scheduler turns registered systems into an **execution plan**: an ordered list of
groups. Groups run one after another; systems within a group run concurrently against
the same snapshot, and their buffered changes are applied together at the group
boundary.

Which systems land in which group is decided by a pluggable `ExecutionGroupBuilder`
callable. The shipped implementation, `build_single_group_plan`, gives each dev-mode system a group of
its own and puts every other system into a single parallel group.

When two systems in a group write the same component on the same entity, the conflict is
not prevented — it is *resolved at apply time*. Repeated writes to the same
`(entity, type)` fold through `Combinable.__combine__` if the component implements it,
and otherwise resolve last-writer-wins in system registration order.

!!! note "Declared, not yet scheduled"
    `frequency` and `phase` can be set on a system today, and static write-conflict
    analysis exists as `queries_disjoint()`, but no shipped scheduler consumes any of
    them — every registered system runs every tick. Dependency-ordered and
    frequency-based execution are planned as alternative group builders. See
    [Invariants and Known Gaps](../architecture/invariants.md#declared-but-not-wired).

### Future: Learned Scheduling

In future versions of AgentECS, we plan to introduce learned scheduling capabilities.
By providing metrics such as execution time, latency, token-usage and performance outcomes, the scheduler can learn optimal execution strategies over time. These schedules are stored as part of the world state and can be used preferentially when similar conditions arise.


## Storage, Performance and Sharding

The world state does not hold component data itself. It delegates to a pluggable
`Storage` backend, which is the seam that will eventually allow archetypal layouts,
persistence, and cross-shard distribution without any change to systems.

The shipped backend, `LocalStorage`, is deliberately simple: nested dictionaries keyed
by entity and then by component type, with queries as an O(n) scan. It is correct and
easy to reason about, not fast. Cache-efficient archetypal storage is on the
[Roadmap](roadmap.md).

`EntityId` already carries a `shard` field, always `0` today, so that entity identity
does not have to change when distribution arrives.

See [Storage](storage.md) for the protocol, and
[Invariants and Known Gaps](../architecture/invariants.md#performance-characteristics)
for the current cost of each operation.
