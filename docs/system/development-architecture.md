# Development and Code Architecture

This page is a quick reference for contributors working on AgentECS internals.
For a walkthrough of what the code in each layer actually does, see the
[Architecture Deep Dive](../architecture/index.md).

## Development workflow

1. Create a branch for each change.
2. Run checks locally before opening a PR:
   - `task check` for lint, format, type checks, and tests
   - `task lint:imports` for import contract validation
3. Keep changes scoped and atomic (one logical change per commit).
4. Update docs when public behavior or architecture contracts change.

## Runtime layers

AgentECS runtime code in `src/agentecs/` is organized by kind, and the kinds form
the dependency order.

| Layer | Folder | Responsibility |
| --- | --- | --- |
| 1 (outer) | `adapters/` | External integrations: Chroma, Instructor |
| 2 | `api/` | Public entry points: the `@component` / `@system` decorators and the pre-wired `World` |
| 3 | `services/` | Stateful concerns: registry, storage, scheduler, world |
| 4 | `functions/` | Pure functions over models |
| 5 | `protocols/` | Structural protocols: the framework's swappable seams |
| 6 (inner) | `models/` | Frozen dataclasses, enums, and plain value types |

Dependency flow is top-to-bottom (outer layers import inner layers).

### Layer notes

- `models/` and `protocols/` are importable from anywhere. `models/` imports only
  other models; `protocols/` imports only models.
- `functions/` hold no state and do no I/O. Anything that keeps state is a service.
- Each service under `services/` owns one concern and never imports another
  service. `services/world/` and `services/storage/` are multi-file because each
  is one concern spread over a few modules, not several concerns.
- `services/world/World` takes `Storage` and `ExecutionStrategy` as required
  arguments. `api/world.py` is the composition root that fills in `LocalStorage`
  and `SimpleScheduler`.

## Other folders under `src/agentecs/`

- `standard_library/`: reusable higher-level ECS patterns.
- `_rust/`: Rust-backed extensions.

## Import contracts

Import boundaries are enforced by `.importlinter` and checked via `task lint:imports`.

### `layers` (layers contract)

Defines runtime dependency direction:

1. `agentecs.adapters`
2. `agentecs.api`
3. `agentecs.services`
4. `agentecs.functions`
5. `agentecs.protocols`
6. `agentecs.models`

### `services_independent` (independence contract)

`agentecs.services.registry`, `agentecs.services.storage`,
`agentecs.services.scheduler` and `agentecs.services.world` must not import each
other. There are no exceptions.

### `no_root_facade_imports` (forbidden contract)

Internal runtime modules (`models`, `protocols`, `functions`, `services`, `api`,
`adapters`) must not import the root facade module `agentecs`.
