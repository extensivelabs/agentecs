# Invariants and Known Gaps

What the runtime actually guarantees today, and where the API promises more than the
implementation delivers. Every behaviour on this page was verified against the code at
`a6925a2`, not inferred from docstrings.

---

## Guaranteed invariants

These hold, and code may rely on them.

### Identity

- An `EntityId` is immutable and self-describing. It holds no reference to a world.
- A recycled index always carries a higher `generation`. A stale handle fails
  `EntityAllocator.is_alive()` rather than addressing its successor.
- User entities start at index 1000. Indices below that are reserved for singletons.
- Provisional spawn IDs are negative and therefore cannot collide with allocated ones.

### Components

- A component type's ID is `sha256(module.qualname)` truncated to 64 bits — identical in
  every process running the same code. Collisions raise at registration.
- `@component` requires a dataclass or Pydantic model, and must be applied *after*
  `@dataclass`.
- `__combine__` and `__split__` are always reached through
  `combine_protocol_or_fallback` / `split_protocol_or_fallback`, so the fallback (LWW,
  and deep-copy respectively) always applies when the protocol is absent.

### Reads

- **Every read returns a deep copy.** `ScopedAccess.get()`, `query()`, `World.get_copy()`,
  and `World.query_copies()` all copy. Mutating what you read changes nothing; you must
  write the value back.
- A system can only read types its descriptor allows. Dev-mode systems bypass this.
- A system sees its own buffered writes. It never sees a peer's writes from the same
  execution group.

### Writes

- Writes from a system are buffered as ordered `MutationOp`s and never touch storage
  during execution.
- `op_seq` is authoritative. When the ordered op log and a convenience projection
  (`result.updates`, `result.inserts`, …) disagree, the op log wins.
- Within one applied result, repeated writes to the same `(entity, type)` fold through
  `__combine__` when the component is `Combinable`, and overwrite otherwise.
- `merge_entities` and `split_entity` always create new entities and destroy their
  inputs. Neither mutates in place.

### Execution

- Groups run sequentially; systems within a group run concurrently.
- Results are concatenated in **registration order** before being applied.
- Each retry attempt gets a fresh buffer — a failed attempt's partial writes are
  discarded, not replayed.

---

## Sharp edges

Real behaviour that surprises people. All verified.

### Singleton entities are invisible to queries

`_ensure_system_entities()` (`world/world.py:71`) creates `WORLD` and `CLOCK` by writing
`_storage._components[entity] = {}` directly, bypassing the allocator. The allocator
therefore has no generation record for index 0 or 1, so `is_alive()` returns `False`
for both.

Consequences, all observable:

```python
world._storage.entity_exists(SystemEntity.WORLD)   # False
world.set_singleton(Cfg(5))
world.singleton_copy(Cfg)                          # Cfg(n=5)   ← works
list(world.query_copies(Cfg))                      # []         ← invisible
list(world._storage.all_entities())                # []         ← invisible
```

`get_component` works because it only checks dict membership, while `query` and
`all_entities` additionally filter on `is_alive`.

The same asymmetry explains why `ScopedAccess` has a separate `update_singleton()`:
`update(SystemEntity.WORLD, ...)` raises `KeyError: Entity ... does not exist`, whereas
`update_singleton()` deliberately skips the existence check.

**Reach singletons through `singleton()` / `update_singleton()` only.** Never expect
them in a query result.

### Reads fail differently inside and outside systems

| Call | Component missing |
| --- | --- |
| `World.get_copy(e, T)` | returns `None` |
| `ScopedAccess.get(e, T)` | raises `KeyError` |

The type annotations do not reflect this. `ScopedAccess.get` is annotated `Copy[T]` but
raises; `EntityHandle.__getitem__` and the `ReadOnlyAccess` protocol both advertise
`T | None`. The `if result is None` branch in `ScopedAccess.singleton()`
(`world/access.py:504`) is consequently unreachable — `get()` raises first.

### Same-tick reads diverge from what gets committed

For a `Combinable` component written twice by one system, the buffer overlay returns the
*latest* value while apply time folds *both*:

```python
@system(reads=(Log,), writes=(Log,))
def s(world):
    world[e, Log] = Log(["s1"])
    world[e, Log] = Log(["s1b"])
    world[e, Log]          # ['s1b']        ← what you read
# after tick:              # ['s1', 's1b']  ← what was committed
```

Tracked as `REQ-062`. Until it lands, do not read back a `Combinable` you just wrote and
expect the committed value.

### Provisional spawn IDs are not remapped

An entity spawned inside a system gets a negative placeholder. `apply_result_async`
allocates the real ID and returns it, but does not rewrite later ops that reference the
placeholder. Writes addressed to the provisional ID are lost.

Pass everything the new entity needs into the `spawn()` call. Tracked as `REQ-039`.

### The subscript key is ignored on write

`world[entity, Position] = value` infers the component type from `value`. The `Position`
in the key is never read. Assigning a `Velocity` under a `Position` key silently records
a `Velocity` update.

### Returned mutations skip existence checks

Imperative mutations go through `_check_writable` **and** `_check_entity_exists`.
Mutations returned from a system go through `normalize_result` → `merge` →
`validate_result_access`, which checks the *write contract* only. A returned write to an
unknown or destroyed entity still reaches `apply_result_async`.

`validate_result_access` also only inspects `updates` and `inserts` — returned removes,
spawns, and destroys are unchecked — and returns immediately for `AllAccess` systems.
This is the open review item from PR #89.

### Parallel systems combine independently computed values

Two systems in a group both start from the same state. If both write a `Combinable`
component computed from that starting value, `__combine__` receives two *full* values,
not a base and a delta. Implementations must be additive or idempotent; treating
`other` as an increment on `self` will double-count.

### `World.tick()` is `asyncio.run`

Both `tick()` and `apply_result()` call `asyncio.run` and will fail inside an existing
event loop. Use `tick_async()` / `apply_result_async()` from async code.

---

## Declared but not wired

These exist in the API surface and have no effect on runtime behaviour. They are design
intent, useful as documentation, and safe to use — but do not expect them to do
anything yet.

| Surface | Where | Status |
| --- | --- | --- |
| `SystemDescriptor.frequency` | `core/system/models.py:30` | Stored, never read by any scheduler. Every system runs every tick. |
| `SystemDescriptor.phase` | `core/system/models.py:30` | Stored, never read anywhere. |
| `SystemMode.PURE` | `core/system/models.py:14` | Accepted by `@system`. `_check_writable` only special-cases `READONLY`, so a PURE system can still mutate through `ScopedAccess`. |
| `queries_disjoint()` | `core/query/operations.py:17` | Implemented and property-tested. No scheduler calls it. |
| `Query.excluding()` | `core/query/models.py:43` | Enforcement is type-level: `QueryAccess` is flattened via `.types()` before checks, so exclusions never restrict which entities you may write. |
| Conflict detection | — | `SingleGroupBuilder` puts every non-dev system in one parallel group. No write-conflict analysis exists. Conflicts resolve at apply time by `__combine__` or LWW. |
| `tracing/` | `tracing/protocol.py` | `HistoryStore` and `TickRecord` are protocol and model only. `World` neither counts ticks nor emits records. |
| `SystemEntity.SCHEDULER` | `core/identity/models.py:46` | Reserved. `_ensure_system_entities` creates only `WORLD` and `CLOCK`. |
| `ConflictError` | `world/result.py:356` | Defined, never raised. |
| `Access` enum | `core/system/models.py:22` | Defined, unused. |
| `_rust/` | `_rust/__init__.py` | Empty placeholder for future PyO3 bindings. |
| `standard_library/` | — | Empty package skeleton. |

Storage-side strictness is a partial case. REQ-040 tightened write policy at the
`ScopedAccess` layer, but `LocalStorage.set_component` (`storage/local.py:146`) still
creates a component bucket for an unknown entity rather than raising. The guard lives in
the access layer, not the storage layer.

---

## Performance characteristics

Not optimized, and deliberately so at this stage.

| Operation | Cost | Note |
| --- | --- | --- |
| `LocalStorage.query` | O(n) over all entities | Archetypal storage would make it O(matched). |
| Every read | two deep copies | Once out of storage, once through the buffer overlay. |
| `result.updates` and siblings | O(ops) per access | Materialized on every property access. `_query_raw_async` caches them against `_next_op_seq`; other callers do not. |
| `ScopedAccess.get` from sync code | thread hop | Marshalled onto the `SyncRunner` loop via `run_coroutine_threadsafe`. |
| `snapshot()` / `restore()` | `pickle` | Marked in-source as prototype-only. |

The async-everywhere internal design costs a thread hop per synchronous read today. It
buys the ability to put a genuinely remote storage backend behind the same `Storage`
protocol without changing a single system.
