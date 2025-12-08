# Roadmap

## Current Status (v0.1.0)

Core ECS implementation:

- Entity identity with generational indices
- Component registry and decorator
- System decorator with access control
- World coordination and scoped access
- Local storage backend
- Basic parallel scheduler
- Async-first architecture
- LLM and vector database integrations

## Roadmap

### Advanced Scheduling

- Frequency-based system execution
- Dependency-based execution
- Learnable scheduler optimization (context efficiency and cache-awareness)

### Standard Library systems

- Roles, Planning, and Memory
- Task management systems
- Context management systems
- Tool use, MCP and A2A protocol systems
-

### Component Operations

- Shared and owned component management
- Standard library contains resource allocation mechanisms (queues, bidding)

### Storage Backend
- Archetypal storage for cache-efficient queries
- Serialization and persistence
- Cross-process storage (Redis, etc.)

### External Integrations
- MCP (Model Context Protocol) adapter
- A2A (Agent-to-Agent) protocol support

## Long Term

### Distributed Scaling
- Multi-node execution
- Shard-based entity distribution
- Cross-shard queries
- Consistency models (eventual/strong)
- Network communication layer

### Rust Backend
- PyO3 bindings for performance-critical operations
- Rust storage implementation
- Rust query engine
- Hybrid Python/Rust architecture

### Research Features
- Topology components (spatial, graph-based)
- Local parameter systems (proximity effects)
- Information aggregation mechanisms (voting, consensus)
- Contested resource management
- Agent merging/splitting research
