# First Steps

Let's build your first AgentECS application: a simple task management system for AI agents. You'll learn the three core elements of ECS by implementing agents that process tasks.

## Your First Agent

Create a new file `my_first_agent.py`:

```python
from dataclasses import dataclass
from enum import Enum
from agentecs import World, component, system, ScopedAccess

# Step 1: Define components (data)
class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@component
@dataclass
class Task:
    description: str
    status: TaskStatus

@component
@dataclass
class TokenBudget:
    available: int
    used: int

# Step 2: Define a system (behavior)
@system(reads=(Task, TokenBudget), writes=(Task, TokenBudget))
def process_tasks(world: ScopedAccess) -> None:
    """Process pending tasks if tokens are available."""
    for entity, task, budget in world(Task, TokenBudget):
        if task.status == TaskStatus.PENDING and budget.available >= 100:
            # Simulate task processing
            new_task = Task(task.description, TaskStatus.COMPLETED)
            new_budget = TokenBudget(
                available=budget.available - 100,
                used=budget.used + 100
            )
            world[entity, Task] = new_task
            world[entity, TokenBudget] = new_budget
            print(f"Entity {entity.index} completed: {task.description}")
            print(f"  Tokens remaining: {new_budget.available}")

# Step 3: Create world and entities
world = World()

# Spawn agents with tasks
agent1 = world.spawn(
    Task("Analyze user feedback", TaskStatus.PENDING),
    TokenBudget(available=500, used=0)
)

agent2 = world.spawn(
    Task("Generate summary report", TaskStatus.PENDING),
    TokenBudget(available=150, used=0)
)

# Register system
world.register_system(process_tasks)

# Run simulation
for tick in range(3):
    print(f"\n=== Tick {tick + 1} ===")
    world.tick()
```

Run it:

```bash
python my_first_agent.py
```

You should see agents processing tasks when they have enough tokens:

```
=== Tick 1 ===
Entity 0 completed: Analyze user feedback
  Tokens remaining: 400
Entity 1 completed: Generate summary report
  Tokens remaining: 50

=== Tick 2 ===
Entity 0 completed: Analyze user feedback
  Tokens remaining: 300

=== Tick 3 ===
Entity 0 completed: Analyze user feedback
  Tokens remaining: 200
```

## Understanding the Code

### Components are Data

Components hold state. They're just dataclasses:

```python
@component
@dataclass
class Task:
    description: str
    status: TaskStatus
```

The `@component` decorator registers them with AgentECS so they can be queried.

### Systems are Behavior

Systems define what happens each tick. They query for entities with specific components:

```python
@system(reads=(Task, TokenBudget), writes=(Task, TokenBudget))
def process_tasks(world: ScopedAccess) -> None:
    for entity, task, budget in world(Task, TokenBudget):
        # Process task...
```

The `reads=` and `writes=` declarations are **optional** but help with:
- Documentation (what does this system do?)
- Validation (catching bugs early)
- Parallelization (safe concurrent execution)

### Entities are IDs

Entities are lightweight identifiers. When you spawn:

```python
agent = world.spawn(Task(...), TokenBudget(...))
```

You get back an `EntityId`. The components are stored separately, accessed via queries.

### Queries Find Patterns

The query `world(Task, TokenBudget)` finds all entities with **both** components:

```python
for entity, task, budget in world(Task, TokenBudget):
    # Only entities with Task AND TokenBudget
```

### Copy-on-Read Pattern

**Important:** Reads return **copies** by default. You must write back changes:

```python
# task is a COPY, not a reference
new_task = Task(task.description, TaskStatus.COMPLETED)
world[entity, Task] = new_task  # Write back required
```

This prevents accidental shared state and enables safe parallelization.

If you need intentional shared component storage, use `Shared(...)` when inserting components.

## Adding More Agents

Let's add multiple agents with different capabilities:

```python
from dataclasses import dataclass
from enum import Enum
from agentecs import World, component, system, ScopedAccess

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@component
@dataclass
class Task:
    description: str
    status: TaskStatus

@component
@dataclass
class Message:
    role: str
    content: str

@component
@dataclass
class Context:
    """Conversation history for an agent."""
    messages: list[Message]

@system(reads=(Task,), writes=(Context,))
def track_conversation(world: ScopedAccess) -> None:
    """Add completed tasks to conversation history."""
    for entity, task in world(Task):
        if task.status == TaskStatus.COMPLETED:
            # Get or create context
            if (entity, Context) in world:
                ctx = world[entity, Context]
                new_messages = ctx.messages + [
                    Message("assistant", f"Completed: {task.description}")
                ]
                world[entity, Context] = Context(new_messages)
            else:
                # Insert new context component
                world.insert(entity, Context([
                    Message("assistant", f"Completed: {task.description}")
                ]))

world = World()

# Spawn three agents
world.spawn(Task("Analyze sentiment", TaskStatus.PENDING))
world.spawn(Task("Extract entities", TaskStatus.PENDING))
world.spawn(Task("Summarize text", TaskStatus.PENDING))

world.register_system(track_conversation)

for tick in range(2):
    print(f"\nTick {tick + 1}:")
    world.tick()
```

All three agents track their conversation history independently.

## Adding Another System

Let's detect when agents are low on resources:

```python
@component
@dataclass
class TokenBudget:
    available: int
    used: int

@system(reads=(TokenBudget,))
def budget_warning(world: ScopedAccess) -> None:
    """Warn when agents are low on tokens."""
    for entity, budget in world(TokenBudget):
        if budget.available < 100:
            print(f"  Warning: Entity {entity.index} low on tokens ({budget.available} left)!")

# Register both systems
world.register_system(process_tasks)
world.register_system(budget_warning)

# Both systems run each tick
world.tick()
```

Systems run **in parallel** by default (unless they conflict). More on this in [Core Concepts](core-concepts.md).

## Complete Example: LLM Agent Workflow

Here's a full working example simulating a simple LLM agent workflow:

```python
from dataclasses import dataclass
from enum import Enum
from agentecs import World, component, system, ScopedAccess

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@component
@dataclass
class Task:
    description: str
    status: TaskStatus

@component
@dataclass
class Message:
    role: str
    content: str

@component
@dataclass
class Context:
    messages: list[Message]
    max_length: int = 10

@component
@dataclass
class TokenBudget:
    available: int
    total: int

@system(reads=(Task, TokenBudget), writes=(Task, TokenBudget, Context))
def process_task_system(world: ScopedAccess) -> None:
    """Process tasks using token budget."""
    for entity, task, budget in world(Task, TokenBudget):
        if task.status == TaskStatus.PENDING and budget.available >= 100:
            # Process task
            world[entity, Task] = Task(task.description, TaskStatus.COMPLETED)
            world[entity, TokenBudget] = TokenBudget(
                available=budget.available - 100,
                total=budget.total
            )

            # Add to context
            msg = Message("assistant", f"Completed: {task.description}")
            if (entity, Context) in world:
                ctx = world[entity, Context]
                new_messages = (ctx.messages + [msg])[-ctx.max_length:]
                world[entity, Context] = Context(new_messages, ctx.max_length)
            else:
                world.insert(entity, Context([msg]))

@system(reads=(TokenBudget,))
def monitor_budget_system(world: ScopedAccess) -> None:
    """Monitor token usage."""
    for entity, budget in world(TokenBudget):
        used_pct = (budget.total - budget.available) / budget.total * 100
        if used_pct > 80:
            print(f"Entity {entity.index}: {used_pct:.0f}% tokens used")

@system(reads=(Task,))
def cleanup_system(world: ScopedAccess) -> None:
    """Remove completed tasks."""
    to_remove = []
    for entity, task in world(Task):
        if task.status == TaskStatus.COMPLETED:
            to_remove.append((entity, Task))

    for entity, component_type in to_remove:
        world.remove(entity, component_type)

# Setup
world = World()

world.spawn(
    Task("Analyze customer feedback", TaskStatus.PENDING),
    TokenBudget(available=1000, total=1000)
)

world.spawn(
    Task("Generate weekly report", TaskStatus.PENDING),
    TokenBudget(available=200, total=1000)
)

world.register_system(process_task_system)
world.register_system(monitor_budget_system)
world.register_system(cleanup_system)

# Run
for tick in range(3):
    print(f"\n=== Tick {tick + 1} ===")
    world.tick()
```

## Next Steps

You've learned the basics:

- **Components** hold data (Task, Message, Context, TokenBudget)
- **Systems** define behavior (process tasks, track context, monitor resources)
- **Entities** combine components
- **Queries** find patterns
- **Copy-on-read** prevents accidental shared state (with explicit `Shared(...)` opt-in available)

Ready to dive deeper?

- **[Core Concepts](core-concepts.md)**: Learn about snapshot isolation, parallel execution, and async systems
- **[Cookbook](../cookbook/index.md)**: Practical patterns and examples
- **[Task Dispatch Example](../../examples/task_dispatch/)**: See a complete LLM-based agent system

## Common Questions

**Q: Do I need to specify `reads` and `writes`?**

No. For prototyping, use `@system()` for full read/write access. If you declare only one side, the omitted side defaults to no access (for example `@system(reads=(Task,))` means read-only for `Task` unless you also declare writes).

**Q: Can systems be async?**

Yes! Just define them with `async def`:

```python
@system(reads=(Task,), writes=(Response,))
async def llm_system(world: ScopedAccess) -> None:
    # await LLM API calls...
```

**Q: How do I access a specific entity?**

Use dict-style access:

```python
task = world[agent, Task]  # Read
world[agent, Task] = new_task  # Write
```

**Q: What if I query components an entity doesn't have?**

The query simply won't match that entity. Queries are safe and return only entities with **all** requested components.

**Q: How do I add a component to an existing entity?**

Use `world.insert()`:

```python
world.insert(entity, Context([]))
```

Or within a system:

```python
@system()
def add_context(world: ScopedAccess) -> None:
    for entity, task in world(Task):
        if (entity, Context) not in world:
            world.insert(entity, Context([]))
```
