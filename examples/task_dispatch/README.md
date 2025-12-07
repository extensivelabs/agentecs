# Task Dispatch Example

A comprehensive example demonstrating AgentECS capabilities through a dynamic task dispatch system with LLM-based agents.

## What This Demonstrates

- **Dynamic Agent Spawning**: Agents are created on-demand for unassigned tasks
- **LLM Integration**: Claude-powered agents with structured outputs via AgentECS's InstructorAdapter
- **Multi-Turn Reasoning**: Agents can think through problems over multiple ticks
- **User Interaction**: Agents can ask clarifying questions and incorporate feedback
- **ECS-Idiomatic Design**: Task components move from queue to agent entities
- **Lifecycle Management**: Automatic cleanup when tasks complete

## Architecture

### Components

- **`Task`**: Unit of work with lifecycle state (UNASSIGNED → ASSIGNED → IN_PROGRESS → WAITING_FOR_INPUT/COMPLETED)
- **`TaskQueue`**: Singleton holding only unassigned tasks
- **`AgentState`**: Agent's system prompt, conversation history, and iteration count

### Systems

1. **`TaskAssignmentSystem`**: Monitors TaskQueue and spawns agents for unassigned tasks
2. **`AgentProcessingSystem`**: Processes agents with LLM calls, handles DEEP_THOUGHT/ASK_USER/FINAL_ANSWER responses
3. **`AgentCleanupSystem`**: Destroys agents whose tasks are complete

### ECS Design Highlights

```python
# Task moves from queue to agent entity
queue = world.singleton(TaskQueue)
task = queue.tasks.pop()
world.spawn(AgentState(...), task)  # Task now on agent entity!

# Natural querying - no ID lookups needed
for entity, agent_state, task in world(AgentState, Task):
    # Both components paired on same entity
    process_agent(agent_state, task)
```

## Prerequisites

- Python 3.11+
- AgentECS with LLM support: `pip install agentecs[llm]`
- Anthropic API key for Claude

## Setup

1. **Set API Key**:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```

2. **Optional Configuration** (via environment variables):
   ```bash
   export LLM_MODEL=claude-sonnet-4-5-20250514
   export LLM_TEMPERATURE=0.7
   export LLM_MAX_TOKENS=2000
   export MAX_ITERATIONS=10
   ```

## Running the Example

```bash
# From repository root
python examples/task_dispatch/main.py

# Or using task runner
task run -- examples/task_dispatch/main.py
```

## Example Output

```
================================================================================
Task Dispatch Example - Dynamic Agent Spawning with LLM Processing
================================================================================

World initialized with 4 tasks

Tick 1
----------------------------------------
Spawned agent for task: a3f7b2c4... (Write a haiku about the joy of programming)
Spawned agent for task: d9e1f6a8... (Explain the pros and cons of remote work)
...

Tick 2
----------------------------------------
Agent 1 (iter 1) thinking: Crafting a haiku that captures the essence...
Agent 2 asks: Would you like me to focus on any specific aspect of remote work?

Task 'd9e1f6a8...' asks:
   Would you like me to focus on any specific aspect of remote work?

Your response: Focus on work-life balance and productivity

...

Agent 1 completed: Code flows like water / Bugs become elegant art / Joy in creation
Cleaning up agent 1 (task a3f7b2c4... completed)
```

## Example Tasks

The example includes diverse task types:

- **Creative**: "Write a haiku about the joy of programming"
- **Analytical**: "Explain the pros and cons of remote work in 3 bullet points"
- **Computational**: "Calculate what a 15% tip on a $47.50 bill would be"
- **Synthesis**: "Summarize the key benefits of ECS architecture"

## Key Implementation Details

### Using AgentECS's LLM Adapter

```python
from anthropic import Anthropic, AsyncAnthropic
from agentecs.adapters import Message
from agentecs.adapters.instructor import InstructorAdapter
from agentecs.config import LLMSettings

# Create adapter
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
async_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

adapter = InstructorAdapter.from_anthropic(
    client,
    settings=LLMSettings(model="claude-sonnet-4-5-20250514"),
    async_client=async_client,
)

# Call with structured output
messages = [Message.system("..."), Message.user("...")]
response = await adapter.call_async(messages, response_model=AgentResponse)
```

### Multi-Turn Reasoning

```python
# Conversation history accumulates across ticks
agent_state.conversation_history.append({
    "role": "assistant",
    "content": f"[Thinking] {response.reasoning}\n{response.message}"
})

# Next tick, agent sees all previous thinking
messages = build_messages(agent_state, task)
response = await call_agent(system_prompt, messages, AgentResponse)
```

### Task Lifecycle

```python
# 1. UNASSIGNED: Task in TaskQueue singleton
queue.add_task("Write a poem")

# 2. ASSIGNED: Task moved to agent entity
world.spawn(AgentState(...), task)

# 3. IN_PROGRESS: Agent thinking or processing
if response.response_type == ResponseType.DEEP_THOUGHT:
    task.status = TaskStatus.IN_PROGRESS

# 4. WAITING_FOR_INPUT: Agent needs user response
elif response.response_type == ResponseType.ASK_USER:
    task.user_query = response.message
    task.status = TaskStatus.WAITING_FOR_INPUT

# 5. COMPLETED: Agent finished
elif response.response_type == ResponseType.FINAL_ANSWER:
    task.result = response.message
    task.status = TaskStatus.COMPLETED

# 6. Cleanup: Agent destroyed (Task component removed too)
world.destroy_entity(entity)
```

## Customization

### Add Your Own Tasks

```python
EXAMPLE_TASKS = [
    "Your custom task description here",
    "Another task...",
]
```

### Adjust Configuration

```python
# In systems.py
MAX_ITERATIONS = 10  # Prevent infinite loops

# In llm_utils.py
settings = LLMSettings(
    model="claude-sonnet-4-5-20250514",
    temperature=0.7,
    max_tokens=2000,
)
```

### Modify Agent Behavior

The `AgentResponse` model in `models.py` defines the structured output:

```python
class AgentResponse(BaseModel):
    reasoning: str  # Chain-of-thought
    response_type: ResponseType  # DEEP_THOUGHT | ASK_USER | FINAL_ANSWER
    message: str  # Content based on type
```

## Extending the Example

### Version 2: Full ECS User Interaction

The planning documents (`.agents/EXAMPLE_TASK_DISPATCH.md`) describe a "Version 2" where user interaction is also managed via components and systems:

- `PendingUserQueries` component: Aggregated queries
- `UserResponse` component: Raw user input
- `QueryAggregationSystem`: Formats questions with LLM
- `ResponseParsingSystem`: Parses and routes responses with LLM

### Additional Features

- **Task Prioritization**: Add priority to Task component, process high-priority first
- **Agent Specialization**: Different agent types for different task categories
- **Result Validation**: Add validation system to check task completeness
- **Metrics**: Track iteration counts, success rates, average completion time

## Architecture Benefits

This example showcases ECS design principles:

1. **Composition over Hierarchy**: Agents are just entities with AgentState + Task components
2. **Emergent Behavior**: No explicit workflow graph - behavior emerges from system interactions
3. **Dynamic Reconfiguration**: Tasks move between queue and agents naturally
4. **Query Simplicity**: `world(AgentState, Task)` gets exactly what's needed
5. **Automatic Cleanup**: Destroying entity removes all components (no orphaned data)

## Troubleshooting

### API Key Issues

```
ValueError: No ANTHROPIC_API_KEY found
```

**Solution**: Set the environment variable:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### Import Errors

```
ImportError: instructor is required
```

**Solution**: Install with LLM support:
```bash
pip install agentecs[llm]
```

### Max Iterations Reached

```
Agent 1 hit max iterations (10), completing task
```

**Solution**: Increase MAX_ITERATIONS or simplify tasks. This is a safety guard to prevent infinite loops.

## Related Examples

- `examples/simple_agents.py`: Basic ECS concepts
- `examples/proximity_merge.py`: Agent merging based on opinion convergence
- `examples/task_splitting.py`: Dynamic agent splitting

## Learn More

- [AgentECS Documentation](../../docs/index.md)
- [Core Concepts](../../docs/start-up/core-concepts.md)
- [Systems Guide](../../docs/system/systems.md)
- [LLM Adapters](../../docs/adapters/llm.md)
