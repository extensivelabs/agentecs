"""Task Dispatch Example for AgentECS.

This example demonstrates AgentECS capabilities through a dynamic task dispatch system:

- **Dynamic Agent Spawning**: Agents are spawned on-demand for unassigned tasks
- **LLM Integration**: Each agent uses Claude to process its task with structured outputs
- **Multi-Turn Reasoning**: Agents can think through problems over multiple ticks
- **User Interaction**: Agents can ask clarifying questions and incorporate user feedback
- **Lifecycle Management**: Agents are automatically cleaned up when tasks complete

## Architecture

The example uses an ECS-idiomatic design where:
- `Task` components move from a singleton queue to agent entities when assigned
- Querying `world(AgentState, Task)` naturally gets agents with their tasks
- No ID cross-referencing needed - components are paired on the same entity
- Task lifecycle is reflected by component location (queue vs agent entity)

## Running the Example

```bash
# Set up API key
export ANTHROPIC_API_KEY=your_key_here

# Run the example
python examples/task_dispatch/main.py

# Or use task runner
task run -- examples/task_dispatch/main.py
```

## Components

- `Task`: Task description, status, result, and user interaction state
- `TaskQueue`: Singleton holding unassigned tasks
- `AgentState`: Agent's system prompt, conversation history, iteration count

## Systems

1. `TaskAssignmentSystem`: Spawns agents for unassigned tasks
2. `AgentProcessingSystem`: Processes agents with LLM calls
3. `AgentCleanupSystem`: Destroys agents whose tasks are complete
"""
