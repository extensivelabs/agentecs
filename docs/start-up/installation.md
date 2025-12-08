# Installation

AgentECS is a Python framework requiring Python 3.11 or higher.

## Quick Install

Install the core framework from PyPI:

```bash
pip install agentecs
```

This provides the minimal installation with just the ECS core functionality.

## Optional Dependencies

AgentECS uses optional dependencies for additional features. Install them as needed:

### Configuration Support

For Pydantic-based components and configuration:

```bash
pip install agentecs[config]
```

Enables:
- Pydantic models as components
- Automatic validation
- Configuration management

### Retry Logic

For automatic retry with exponential backoff:

```bash
pip install agentecs[retry]
```

Enables:
- Configurable retry policies in scheduler
- Exponential/linear backoff
- Graceful failure handling for transient errors

### Vector Storage

For ChromaDB-based vector storage (future):

```bash
pip install agentecs[chroma]
```

### LLM Integration

For built-in LLM client adapters (future):

```bash
pip install agentecs[llm]
```

### All Optional Dependencies

To install everything:

```bash
pip install agentecs[all]
```

Equivalent to:
```bash
pip install agentecs[config,retry,chroma,llm]
```

## Development Installation

For contributing to AgentECS or running examples:

### Clone Repository

```bash
git clone https://github.com/extensivelabs/agentecs
cd agentecs
```

### Set Up Development Environment

AgentECS uses `uv` for fast dependency management and `task` for build automation.

**Automatic Setup:**

```bash
./scripts/bootstrap.sh
task setup
```

This will:
1. Install `uv` if not present
2. Create virtual environment
3. Install all dependencies (including dev dependencies)
4. Set up pre-commit hooks

**Manual Setup:**

If you prefer manual setup:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install pre-commit hooks
uv run pre-commit install
```

### Verify Installation

Run tests to verify everything works:

```bash
task test
```

Run a simple example:

```bash
uv run python examples/simple_agents.py
```

### Development Tasks

AgentECS uses `task` (Taskfile) for common development operations:

```bash
# Run all tests
task test

# Run type checking
task type-check

# Run linting
task lint

# Auto-fix linting issues
task lint-fix

# Build documentation
task docs

# List all available tasks
task --list
```

## Verify Installation

Check your installation:

```python
import agentecs
print(agentecs.__version__)

# Try a simple example
from dataclasses import dataclass
from agentecs import World, component, system, ScopedAccess

@component
@dataclass
class Position:
    x: float
    y: float

@system(reads=(Position,), writes=(Position,))
def move_right(world: ScopedAccess) -> None:
    for entity, pos in world(Position):
        world[entity, Position] = Position(pos.x + 1, pos.y)

world = World()
entity = world.spawn(Position(0, 0))
world.register_system(move_right)
world.tick()

pos = world.get_component(entity, Position)
assert pos.x == 1  # Entity moved right
print("✓ AgentECS is working!")
```

## System Requirements

- **Python**: 3.11 or higher
- **Operating Systems**: Linux, macOS, Windows
- **Memory**: Minimal for core; scales with entity count
- **Dependencies**: Managed via `pyproject.toml`

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'agentecs'`:

- Ensure you activated the virtual environment
- Reinstall with `pip install agentecs` or `uv sync`

### Optional Dependency Errors

If you see errors about missing optional dependencies:

```python
ImportError: Retry policy requires tenacity. Install with: pip install agentecs[retry]
```

Install the required optional dependency group as shown in the error message.

### Development Setup Issues

If `./scripts/bootstrap.sh` fails:

1. Check Python version: `python --version` (must be 3.11+)
2. Install `uv` manually: `pip install uv`
3. Try manual setup steps above

## Next Steps

- Read [Core Concepts](core-concepts.md) to understand ECS fundamentals
- Explore [Quick Example](../index.md#quick-example) for a working system
- Check [System Documentation](../system/index.md) for architecture details
- Browse [Cookbook](../cookbook/index.md) for practical patterns

## Contributing

For detailed development setup and contribution guidelines, see:

- [CONTRIBUTING.md](https://github.com/extensivelabs/agentecs/blob/main/CONTRIBUTING.md)
- [Development Guide](https://github.com/extensivelabs/agentecs/wiki/Development)

Report issues at: [GitHub Issues](https://github.com/extensivelabs/agentecs/issues)
