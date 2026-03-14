# API Reference

Complete API documentation for AgentECS.

## Overview

AgentECS follows a layered architecture separating **stateless functionalities** (core/) from **stateful services** (world/, storage/, scheduling/). The API is organized to reflect this structure:

### Core API
Pure, stateless building blocks for entities, components, systems, and queries. These are the fundamental abstractions that make up the ECS framework.

**Key modules:**
- **Component**: Define components with operation protocols (Combinable, Splittable)
- **Identity**: Entity IDs with generational indices and shard support
- **Query**: Query builder for filtering entities by component types
- **System**: Define systems with access patterns for parallelization

[→ View Core API](core.md)

---

### World API
Central coordination service managing entity lifecycle, component storage, and system execution. The World acts as the orchestrator between your systems and the storage backend.

**Key classes:**
- **World**: Main entry point for entity management and system execution
- **ScopedAccess**: Access control for systems with snapshot isolation
- **EntityHandle**: Convenient wrapper for single-entity operations

[→ View World API](world.md)

---

### Storage API
Storage backend interface and implementations. AgentECS uses a pluggable storage protocol, currently implemented with LocalStorage for single-process use.

**Key modules:**
- **Storage Protocol**: Interface for storage backends
- **LocalStorage**: In-memory implementation with O(n) queries

[→ View Storage API](storage.md)

---

### Scheduling API
Parallel execution engine. The scheduler runs systems in parallel with snapshot isolation, concatenates results in registration order, and relies on world application for Combinable folding and LWW fallback.

**Key classes:**
- **SimpleScheduler**: Parallel execution with group-based orchestration
- **SequentialScheduler**: Alias for SimpleScheduler with max_concurrent=1

[→ View Scheduling API](scheduling.md)

---

### Adapters API
Optional adapters for external integrations including vector stores and LLM access. Adapters implement runtime-checkable protocols and support multiple providers.

**Key modules:**
- **Vector Store**: ChromaDB adapter with typed data models
- **LLM Client**: Instructor adapter for OpenAI, Anthropic, Gemini, LiteLLM
- **Config**: Pydantic Settings for configuration

[→ View Adapters API](adapters.md)

---

## Quick Links

**Getting Started:**
- [Core Concepts](../start-up/core-concepts.md) - Understand entities, components, and systems
- [First Steps](../start-up/first-steps.md) - Your first AgentECS program

**Guides:**
- [Design Philosophy](../system/design-philosophy.md) - Why ECS for AI agents
- [Architecture](../system/architecture.md) - Detailed architecture overview
