# Scheduling Analysis: Snapshot Isolation, Access Patterns, and Update Application

> **Status**: Analysis complete. Decision made → See REQUIREMENTS.md (REQ-009, REQ-010 revised) and TODO.md for implementation plan.

## Decision Summary

After analysis, we're implementing **Option C (Execution Groups with Merge Strategy)** with these specifics:

- **Execution groups**: Infrastructure for N groups, single group for now (all parallel)
- **Merge strategy**: Configurable (LastWriterWins default), sequential application order
- **Access declarations**: Optional (full access if not declared)
- **Diff support**: Deferred, but pipeline designed to allow future injection
- **Concurrency control**: Semaphore-based max_concurrent
- **Retry policy**: Per-system with configurable policy

---

## Executive Summary

You've identified a real conceptual tension in the current design:

1. **Snapshot isolation** guarantees systems don't see each other's changes within a tick
2. **Access pattern scheduling** prevents read-write and write-write conflicts by grouping
3. Under pure snapshot isolation, **read conflicts are never an issue** since all systems see the same initial state
4. **Write conflicts** only matter at merge time, not execution time

**Core Insight**: The current design conflates **execution ordering** (when systems run) with **update ordering** (how results merge). These should be separate concerns.

---

## Current State Analysis

### What We Have

```
┌─────────────────────────────────────────────────────────────┐
│                        TICK EXECUTION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SequentialScheduler:                                        │
│  ┌──────┐   ┌──────┐   ┌──────┐                            │
│  │Sys A │ → │Sys B │ → │Sys C │  All see initial state     │
│  └──┬───┘   └──┬───┘   └──┬───┘                            │
│     │          │          │      Results collected          │
│     ▼          ▼          ▼                                 │
│  ┌──────────────────────────┐                               │
│  │    Apply all results     │  ← Tick boundary              │
│  └──────────────────────────┘                               │
│                                                              │
│  BasicScheduler:                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │  Group 1    │ → │  Group 2    │ → │  Group 3    │       │
│  │ A,B parallel│   │ C alone     │   │ D,E parallel│       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                 │                 │               │
│         ▼                 ▼                 ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Merge+Apply  │  │ Merge+Apply  │  │ Merge+Apply  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                 ↓                 ↓               │
│     G2 sees G1       G3 sees G2                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### The Duplication Problem

| Mechanism | Purpose | Actually Needed? |
|-----------|---------|------------------|
| **Snapshot isolation** (buffer per system) | Systems see own writes, not others' | ✅ Yes - isolation semantics |
| **Read-write conflict detection** | Prevent reading stale data | ❌ Not needed under snapshot isolation |
| **Write-write conflict detection** | Prevent race conditions | ⚠️ Execution: No. Merge: Yes |
| **Merge error on same (entity, component)** | Catch conflicts | ⚠️ Could be resolution instead |

**Your observation is correct**: Under snapshot isolation, read conflicts are impossible. Systems always read from the same initial state (plus their own writes). The current scheduler is over-constraining parallelism.

---

## Separation of Concerns

### Two Distinct Problems

```
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION PLAN                │  UPDATE PLAN               │
│  "When do systems run?"        │  "How do results merge?"   │
├────────────────────────────────┼────────────────────────────┤
│                                │                            │
│  Criteria:                     │  Criteria:                 │
│  • Dependencies (A needs B)    │  • Write-write on same     │
│  • Frequency (every N ticks)   │    (entity, component)     │
│  • Resource optimization       │  • Merge semantics         │
│  • Cache/context efficiency    │  • Determinism needs       │
│                                │                            │
│  Output:                       │  Output:                   │
│  Groups/sequence of execution  │  Merge order, resolution   │
│                                │                            │
└────────────────────────────────┴────────────────────────────┘
```

**Current conflation**: We prevent write-write at execution time, when it should be handled at merge time.

---

## Option Analysis

### Option A: Status Quo (Access-Based Conflict Prevention)

**How it works**: Scheduler groups systems so no conflicts exist within a group. Groups execute sequentially. Results merged trivially (no overlaps by construction).

```python
# Current behavior
Group 1: [sys_writes_X, sys_writes_Y]  # No conflict, parallel
Group 2: [sys_writes_X_too]             # Conflicts with G1, sequential
```

**Pros**:
- Simple mental model: conflicts prevented, never encountered
- Deterministic (same result every time)
- Works correctly today

**Cons**:
- Over-constrains parallelism (read-write "conflicts" don't exist)
- Write-write handled by prevention, not resolution
- Doesn't scale to distributed (can't predict all conflicts across nodes)
- Conflates execution order with update application

**Verdict**: ⚠️ Works but conceptually muddled. Limits parallelism unnecessarily.

---

### Option B: Pure Snapshot Isolation (All Parallel)

**How it works**: All systems execute in parallel. All see initial state. Merge all results at tick end with conflict resolution.

```
Tick Start (State S0)
    │
    ├── System A executes (sees S0) → Result A
    ├── System B executes (sees S0) → Result B
    ├── System C executes (sees S0) → Result C
    │
    ▼
Merge(A, B, C) with conflict resolution
    │
    ▼
Tick End (State S1)
```

**Pros**:
- Maximum parallelism (all systems parallel)
- Simpler scheduler (no conflict analysis for execution)
- Clear separation: execution is independent, merge resolves conflicts

**Cons**:
- Needs robust conflict resolution (not just error)
- Non-deterministic unless merge order is fixed
- Loss of granular control (no inter-system dependencies within tick)
- Dependencies become impossible (can't "see" another system's result)

**Verdict**: ⚠️ Maximum parallelism but loses ability to do dependencies within tick.

---

### Option C: Execution Groups with Group-Level Snapshot Isolation (RECOMMENDED)

**How it works**:
- Scheduler creates execution groups based on: **dependencies, frequency, optimization criteria** (NOT read/write conflicts)
- Within each group: snapshot isolation (all parallel, all see same state)
- Between groups: Apply results before next group starts
- Conflict resolution: Per-group merge with deterministic ordering

```
┌────────────────────────────────────────────────────────────────┐
│                          TICK                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Group 1 (based on dependencies/optimization, NOT conflicts)   │
│  ┌──────┐ ┌──────┐ ┌──────┐                                   │
│  │Sys A │ │Sys B │ │Sys C │  ← All see State S0               │
│  └──┬───┘ └──┬───┘ └──┬───┘                                   │
│     │        │        │                                        │
│     └────────┼────────┘                                        │
│              ▼                                                  │
│  ┌─────────────────────────────────────┐                       │
│  │ Merge(A,B,C) with conflict resolution│  ← Deterministic     │
│  │ (e.g., registration order, priority) │                      │
│  └─────────────────────────────────────┘                       │
│              │                                                  │
│              ▼ Apply → State S1                                │
│                                                                 │
│  Group 2 (systems that depend on Group 1 results)              │
│  ┌──────┐ ┌──────┐                                            │
│  │Sys D │ │Sys E │  ← All see State S1                        │
│  └──┬───┘ └──┬───┘                                            │
│     │        │                                                 │
│     └────┬───┘                                                 │
│          ▼                                                     │
│  ┌─────────────────────────────────────┐                       │
│  │ Merge(D,E) with conflict resolution │                       │
│  └─────────────────────────────────────┘                       │
│              │                                                  │
│              ▼ Apply → State S2 (Tick End)                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Execution group criteria** (NOT read/write conflict):
1. Dependencies: System D depends on System A → D in later group
2. Frequency: Some systems run every tick, others every N ticks
3. Resource optimization: Group systems for cache efficiency
4. Everything else: Run in parallel

**Conflict resolution at merge** (NOT prevention):
1. Same (entity, component) written by multiple systems in group
2. Options: Last-writer-wins (deterministic order), Mergeable protocol, error, custom

**Pros**:
- Maximum parallelism within groups (no false read-write constraints)
- Dependencies work (later groups see earlier groups' changes)
- Explicit conflict resolution (user controls merge semantics)
- Clean separation: execution order ≠ merge order
- Scales to distributed (merge-based, not prevention-based)
- Deterministic if merge order is defined

**Cons**:
- More complex than status quo
- Needs well-defined merge semantics
- Changes conceptual model

**Verdict**: ✅ **Recommended**. Best balance of parallelism, future-proofing, and conceptual clarity.

---

### Option D: Event Sourcing / Command Queue

**How it works**: Systems emit commands/events instead of direct writes. Commands queued during execution, applied in deterministic order at tick end.

```python
# Instead of:
access.update(entity, Position(x+1, y+1))

# Systems emit:
access.emit(MoveCommand(entity, delta=(1, 1)))

# At tick end:
for command in sorted(commands, key=timestamp_or_priority):
    command.apply(storage)
```

**Pros**:
- Complete control over update order
- Auditable, replayable
- Distributed-friendly (commands ordered by logical clock)
- Natural CQRS pattern

**Cons**:
- Significant API change (users write commands, not direct updates)
- More boilerplate
- Overhead of command creation
- Loss of "see own writes" semantic within system

**Verdict**: ⚠️ Powerful but invasive. Consider for v2 or as optional mode.

---

### Option E: Hybrid with Configurable Merge (Lightweight Version of C)

**How it works**: Keep current execution model but replace conflict error with configurable merge strategy.

```python
# Configuration
world = World(
    execution=BasicScheduler(),
    merge_strategy=MergeStrategy.LAST_WRITER_WINS,  # or MERGEABLE, ERROR, CUSTOM
)

# Or per-component
@component(merge_strategy=MergeStrategy.MERGEABLE)
@dataclass
class Position:
    x: float
    y: float

    def __merge__(self, other):
        return Position((self.x + other.x) / 2, (self.y + other.y) / 2)
```

**Pros**:
- Minimal change to existing code
- Backwards compatible (ERROR is current behavior)
- Determinism via explicit strategy

**Cons**:
- Still conflates execution and update ordering
- Doesn't address dependencies or optimization criteria

**Verdict**: ⚠️ Good incremental step, but doesn't solve the fundamental conceptual problem.

---

## Distributed Execution Analysis

For distributed execution, the current prevention-based approach **cannot work**:

```
Node 1                    Node 2
┌──────────────┐         ┌──────────────┐
│ System A     │         │ System B     │
│ writes X     │         │ writes X     │
└──────────────┘         └──────────────┘
       │                        │
       └──────────┬─────────────┘
                  ▼
         How do we merge?
```

**You cannot prevent conflicts by scheduling across nodes** - systems execute concurrently with no coordination. You must:

1. **Partition data**: Entity X only lives on one node (shard-based)
2. **Merge at boundary**: Conflict resolution when results combine

This strongly favors **Option C** (group-based with merge resolution) or **Option D** (event sourcing).

---

## Dependencies and Group Boundaries

Your intuition about "ExecutionGroup → Apply → next group" is exactly right for dependencies:

```python
@system(reads=(RawData,), writes=(ProcessedData,))
def process_data(world): ...

@system(reads=(ProcessedData,), writes=(Report,), depends_on=[process_data])
def generate_report(world): ...
```

For dependencies to work, `generate_report` must see `process_data`'s writes. This requires:
1. `process_data` in Group 1
2. Apply Group 1 results
3. `generate_report` in Group 2, sees updated state

**Current scheduler doesn't support this** - it only considers type-level conflicts, not explicit dependencies.

---

## Recommended Path Forward

### Phase 1: Clarify Mental Model (No Code Changes)

Document the separation:
- **Execution Plan**: When systems run (dependencies, frequency, optimization)
- **Merge Plan**: How results combine (conflict resolution)

Update REPO_CONTEXT.md and scheduling docs to reflect this.

### Phase 2: Add Configurable Merge Strategy (Small Change)

Replace `ConflictError` with configurable resolution:

```python
class MergeStrategy(Enum):
    ERROR = auto()           # Current behavior
    LAST_WRITER = auto()     # Registration order wins
    MERGEABLE = auto()       # Use component's __merge__

class BasicScheduler:
    def __init__(self, merge_strategy: MergeStrategy = MergeStrategy.ERROR):
        self._merge_strategy = merge_strategy
```

This is backwards compatible and allows experiments.

### Phase 3: Separate Execution Plan from Conflict Analysis (Medium Change)

Refactor scheduler to:
1. Build execution groups based on **dependencies** (and later frequency, optimization)
2. Within groups: all parallel (true snapshot isolation)
3. Between groups: merge and apply

Access patterns still useful for:
- Validating writes (system wrote what it declared)
- Future: optimization hints for cache/context scheduling

### Phase 4: Add Dependency-Based Scheduling (REQ-011A)

```python
@system(depends_on=[init_system])
def dependent_system(world): ...
```

Scheduler builds dependency graph, topologically sorts into groups.

### Phase 5: Distributed Execution Backend

With merge-based resolution in place, distributed execution becomes feasible:
- Each node executes independently
- Results merge at coordinator
- Conflicts resolved by strategy, not prevented

---

## Summary Table

| Aspect | Current | Recommended (Option C) |
|--------|---------|------------------------|
| Read-write conflict | Prevents parallelism | No constraint (snapshot isolation) |
| Write-write conflict | Prevents parallelism | Merge resolution at group boundary |
| Dependencies | Not supported | Group-based with apply between |
| Frequency | Not supported | Group criteria |
| Determinism | By prevention | By merge order definition |
| Distributed | Not feasible | Merge-based, feasible |
| Complexity | Medium | Higher initially, cleaner long-term |

---

## Answers to Your Questions

**Q: Are read conflicts ever an issue under snapshot isolation?**
No. All systems see the same initial state. Reads cannot conflict.

**Q: When do write conflicts matter?**
Only at merge time. Execution order doesn't matter for correctness (under snapshot isolation).

**Q: Is the current approach over-constraining?**
Yes. Read-write "conflicts" cause unnecessary sequential execution.

**Q: Should execution plan and update plan be separate?**
Yes. The scheduler should focus on **when** to run (dependencies, frequency, optimization). Conflict resolution should focus on **how** to merge (deterministic order, Mergeable protocol).

**Q: For dependencies to work, do we need group → apply → next group?**
Yes. A dependent system needs to see its dependency's results, which requires application between groups.

**Q: What about distributed execution?**
Merge-based resolution is essential. Prevention-based scheduling cannot work across nodes.

---

## Next Steps

1. **Review this analysis** - does it capture your intuition correctly?
2. **Decide on Phase 1-5** - which phases to pursue and in what order
3. **Update REQUIREMENTS.md** if we're changing the scheduler model
4. **Create TODO.md items** for implementation

I recommend starting with Phase 1 (documentation) and Phase 2 (configurable merge) as low-risk improvements that validate the model before larger changes.
