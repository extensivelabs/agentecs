# Contributing to AgentECS

Thank you for your interest in contributing to AgentECS! This document provides guidelines and instructions for contributing to the project.

## Copyright Assignment

**IMPORTANT**: By contributing to AgentECS, you agree that all contributions, including code, documentation, and other materials, are assigned to **ExtensiveLabs** and will be licensed under the project's MIT License. This ensures that ExtensiveLabs can maintain, evolve, and relicense the project as needed while keeping it open source.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

- Python 3.11 or later
- Git
- Basic understanding of ECS (Entity Component System) architecture

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/extensivelabs/agentecs.git
   cd agentecs
   ```

2. **Run the bootstrap script** (installs uv, task, direnv):
   ```bash
   ./scripts/bootstrap.sh
   ```

3. **Restart your shell** or source your shell configuration:
   ```bash
   source ~/.bashrc  # or ~/.zshrc for zsh
   ```

4. **Allow direnv** (if installed):
   ```bash
   direnv allow
   ```

5. **Run the setup script** (creates venv, installs dependencies, sets up hooks):
   ```bash
   ./scripts/setup-dev.sh
   ```

   Or use the task runner:
   ```bash
   task setup
   ```

6. **Verify installation**:
   ```bash
   task test
   task info
   ```

## Development Workflow

### Available Commands

View all available commands:
```bash
task --list
```

Common commands:
- `task test` - Run all tests
- `task test-coverage` - Run tests with coverage report
- `task lint` - Check code with ruff
- `task format` - Auto-format code
- `task type-check` - Run mypy type checking
- `task check` - Run all checks (lint, format, type-check, test)
- `task clean` - Remove build artifacts and caches

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our code style guidelines

3. **Run checks frequently**:
   ```bash
   task check
   ```

4. **Commit your changes** (pre-commit hooks will run automatically):
   ```bash
   git add <files>
   git commit -m "Brief description of changes"
   ```

5. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a pull request** on GitHub

## Code Style

AgentECS follows strict code quality standards:

### Python Style

- **Python version**: 3.11+
- **Formatter**: Ruff (enforced via pre-commit)
- **Linter**: Ruff with rules: E, F, I, N, W, D, UP, B, C4, SIM
- **Type checker**: mypy in strict mode
- **Line length**: 100 characters
- **Docstrings**: Google style

### Type Annotations

- **All functions must have type annotations**
- Use modern type hints (e.g., `list[str]` not `List[str]`)
- Use `from __future__ import annotations` for forward references
- Prefer `Protocol` over abstract base classes

### Code Organization

- **Dataclasses** for simple data structures (with `slots=True` where appropriate)
- **Pydantic models** for data validation
- **Protocols** for interfaces
- **Dependency injection** for testability
- **Pure functions** where possible (especially in `core/`)

### Documentation

- All public functions and classes must have docstrings
- Include usage examples in module-level docstrings
- Comment only where logic isn't self-evident
- Keep comments concise and up-to-date

### Example

```python
"""Module for entity identity management.

Usage:
    allocator = EntityAllocator()
    entity = allocator.allocate()
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityId:
    """Lightweight entity identifier.

    Args:
        shard: Shard identifier for distributed scaling
        index: Unique index within shard
        generation: Generation count for recycling
    """
    shard: int = 0
    index: int = 0
    generation: int = 0

    def is_local(self) -> bool:
        """Check if entity is on local shard."""
        return self.shard == 0
```

## Testing

### Testing Philosophy

AgentECS follows "semantic coverage" - tests should:
- Test guaranteed functionality
- Cover complex cases likely to be missed
- Have a clear reason for existing
- **Not** aim for 100% coverage metrics
- **Focus** on important, non-obvious behavior

### Writing Tests

1. **Use pytest** for all tests
2. **Organize tests** by module (mirror `src/` structure)
3. **Name tests** descriptively: `test_<what>_<condition>_<expected>`
4. **Keep tests focused** - one behavior per test
5. **Use fixtures** for common setup (in `conftest.py`)

### Running Tests

```bash
# All tests
task test

# Unit tests only
task test-unit

# Integration tests only
task test-integration

# With coverage
task test-coverage

# Watch mode (TDD)
task test-watch

# Parallel execution
task test-parallel
```

### Example Test

```python
def test_entity_allocator_recycles_with_generation():
    """Entity allocator should recycle IDs with incremented generation."""
    allocator = EntityAllocator()

    # Allocate and deallocate
    entity1 = allocator.allocate()
    allocator.deallocate(entity1)

    # Next allocation should reuse index with new generation
    entity2 = allocator.allocate()
    assert entity2.index == entity1.index
    assert entity2.generation == entity1.generation + 1
```

## Commit Messages

### Format

```
<type>: <short summary>

<optional detailed description>

<optional footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, tooling

### Examples

```
feat: add Query.excluding() for negative filters

Allows systems to declare queries that exclude certain component types,
enabling more expressive access patterns.

Closes #42
```

```
fix: resolve snapshot isolation bug in ScopedAccess

Systems were seeing other systems' writes within the same tick due to
incorrect buffer merging. Fixed by checking buffer ownership.
```

## Pull Request Process

1. **Ensure all checks pass**:
   - All tests pass
   - Code is formatted (ruff format)
   - No linting errors (ruff check)
   - Type checking passes (mypy)
   - Pre-commit hooks pass

2. **Update documentation**:
   - Add docstrings for new public APIs
   - Update README if adding user-facing features
   - Add examples if helpful

3. **Write tests**:
   - Unit tests for new functionality
   - Integration tests for new workflows
   - Update existing tests if behavior changes

4. **Describe your changes**:
   - Clear PR title and description
   - Link related issues
   - Explain design decisions
   - Note any breaking changes

5. **Copyright assignment**:
   - By submitting a PR, you confirm that you assign all rights to ExtensiveLabs
   - This will be noted in the PR template

6. **Review process**:
   - Maintainers will review your PR
   - Address feedback promptly
   - Keep discussions respectful and constructive

7. **Merging**:
   - PRs require maintainer approval
   - Squash merging is preferred for clean history
   - Delete branch after merging

## Community Guidelines

### Code of Conduct

- **Be respectful** and considerate in all interactions
- **Be collaborative** - we're building this together
- **Be constructive** in feedback and criticism
- **Be patient** - maintainers are volunteers
- **Focus on what's best** for the project and community

### Getting Help

- **Documentation**: Read the README and this guide first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Questions**: Tag maintainers in issues/PRs if needed

### Reporting Issues

When reporting bugs:
- Use the bug report template
- Include minimal reproduction example
- Specify Python version and OS
- Include error messages and stack traces
- Describe expected vs actual behavior

When requesting features:
- Use the feature request template
- Explain the use case and motivation
- Suggest potential implementation approach
- Consider if it aligns with project goals

## Architecture Guidelines

When contributing, keep these principles in mind:

### Core Principles

1. **Stateless Core**: `core/` should be pure protocols and functions
2. **Dependency Injection**: Components receive dependencies explicitly
3. **Protocol-based Design**: Use `Protocol` for interfaces, not inheritance
4. **Snapshot Isolation**: Systems see consistent world state
5. **Access Control**: Systems declare reads/writes upfront

### Layer Responsibilities

- `core/`: Pure protocols, decorators, no state
- `world/`: Stateful coordination, access control
- `storage/`: Pluggable backends implementing storage protocol
- `scheduling/`: Execution orchestration, parallelization
- `adapters/`: External integrations (MCP, A2A, etc.)

### Anti-patterns to Avoid

- Global state (except component registry)
- Systems calling other systems directly
- Mutable default arguments
- Deep inheritance hierarchies
- Over-abstraction for single use cases
- Breaking existing APIs without migration path

## License

By contributing to AgentECS, you agree that your contributions will be assigned to ExtensiveLabs and licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Thank you for contributing to AgentECS!** Your efforts help build better tools for AI agent research and development.
