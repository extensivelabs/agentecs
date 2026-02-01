# Task Dispatch App

An AgentECS example demonstrating LLM-powered agents that dynamically spawn, reason, and interact with users.

## Quick Start

```bash
cd examples/task_dispatch_app
export ANTHROPIC_API_KEY=your_key
python main.py
```

## Usage

```bash
python main.py                    # Interactive mode
python main.py --headless         # Auto-respond to agents
python main.py --viz              # With visualization
python main.py --tasks "Write a poem" "Plan dinner"
```

## How It Works

**Components:**
- `Task` - Work unit with status, description, result
- `TaskQueue` - Singleton holding unassigned tasks
- `AgentState` - Agent's prompt and conversation history

**Systems:**
1. `task_assignment_system` - Spawns agents for queued tasks
2. `agent_processing_system` - Calls LLM, handles responses
3. `agent_cleanup_system` - Destroys completed agents

**Response Types:**
- `DEEP_THOUGHT` - Agent needs more reasoning
- `ASK_USER` - Agent needs clarification
- `FINAL_ANSWER` - Task complete

## Configuration

```bash
export ANTHROPIC_API_KEY=...
export LLM_MODEL=claude-sonnet-4-20250514
export LLM_TEMPERATURE=0.7
export MAX_ITERATIONS=10
```

## Files

```
task_dispatch_app/
├── components.py   # Task, TaskQueue, AgentState
├── models.py       # AgentResponse, ResponseType
├── systems.py      # Three ECS systems
├── llm_utils.py    # LLM client setup
├── world.py        # World creation + viz integration
└── main.py         # CLI entry point
```

## Requirements

See `requirements.txt`. Assumes agentecs is available (e.g., from parent project).
