# Architecture


## Basic Concepts

When setting up your AgentECS-based application, you will work with three primary concepts: Entities, Components, and Systems.

### Entities

Entities represent unique instances, say an agent. Next to their unique identity, entities are collections of components.
They do not contain any behavior themselves.
More than that, the components are not part of the entity, but merely associated with it in the world state.

Learn more about [Entities](entities.md).

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

The scheduling of systems is a critical aspect of the AgentECS architecture.
System declare their needs in terms of:

- **Reads** - Components that the system needs to read.
- **Writes** - Components that the system needs to write.
- **Frequency** - How often the system should run (every tick, every N ticks, on specific events).
- **Conditions** - Any conditions that must be met for the system to run.
- **Dependencies** - Other systems that must run before this system.

The scheduler uses this information to determine the optimal order of system execution, allowing for parallelism where possible.
First, the scheduler identifies systems that need to run in the current tick based on their frequency and conditions.
Next, it resolves dependencies to ensure that systems run in the correct order. Based on the dependency graph, it creates execution groups of systems that can potentially run in parallel. Finally, it checks for access conflicts (e.g., two systems writing to the same component) and adjusts the execution plan accordingly.

### Future: Learned Scheduling

In future versions of AgentECS, we plan to introduce learned scheduling capabilities.
By providing metrics such as execution time, latency, token-usage and performance outcomes, the scheduler can learn optimal execution strategies over time. These schedules are stored as part of the world state and can be used preferentially when similar conditions arise.


## Storage, Performance and Sharding

The world state is designed to be efficient and scalable, supporting large numbers of entities and components.
It does not hold data directly, but rather references to component data stored in optimized data structures.
This design allows for efficient querying and manipulation of entities based on their components.

More details about storage and performance optimizations will be provided in future documentation.
