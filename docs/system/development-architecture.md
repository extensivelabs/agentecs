# Development and Code Architecture

This page is a quick reference for contributors working on AgentECS internals.

## Development workflow

1. Create a branch for each change.
2. Run checks locally before opening a PR:
   - `task check` for lint, format, type checks, and tests
   - `task lint:imports` for import contract validation
3. Keep changes scoped and atomic (one logical change per commit).
4. Update docs when public behavior or architecture contracts change.

## Runtime layers

AgentECS runtime code in `src/agentecs/` is organized by dependency direction.

| Layer | Folders | Responsibility |
| --- | --- | --- |
| 1 (outer) | `adapters/` | External integrations and boundary protocols |
| 2 | `world/`, `scheduling/` | Stateful orchestration and execution planning |
| 3 | `storage/` | Component storage interfaces and backends |
| 4 (inner) | `core/` | Stateless ECS primitives and pure operations |

Dependency flow is top-to-bottom (outer layers import inner layers).

### Layer notes

- `world/` and `scheduling/` are same-level peers and may import each other.
- `storage/` depends on `core/`, but must import leaf modules (not the `core` package facade).
- `core/` should not depend on runtime orchestration layers.

## Other folders under `src/agentecs/`

- `config/`: package configuration helpers.
- `tracing/`: execution history and tracing helpers.
- `standard_library/`: reusable higher-level ECS patterns.
- `_rust/`: Rust-backed extensions.

## Import contracts

Import boundaries are enforced by `.importlinter` and checked via `task lint:imports`.

### `runtime_layers` (layers contract)

Defines runtime dependency direction:

1. `agentecs.adapters`
2. `agentecs.world : agentecs.scheduling`
3. `agentecs.storage`
4. `agentecs.core`

### `no_root_facade_imports` (forbidden contract)

Internal runtime modules (`core`, `storage`, `world`, `scheduling`, `adapters`) must not import the root facade module `agentecs`.

### `storage_core_leaf_imports` (forbidden contract)

`agentecs.storage` must not import `agentecs.core` directly. Use explicit leaf imports from submodules (for example `agentecs.core.component.operations`).
