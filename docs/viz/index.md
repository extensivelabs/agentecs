# Visualization

Real-time visualization for AgentECS worlds. Watch entities spawn, evolve, and interact through an interactive canvas with semantic zoom levels.

!!! note "Separate Package"
    The visualization tool is in a separate repository: [agentecs-viz](https://github.com/extensivelabs/agentecs-viz). This documentation covers usage; for development, see that repository.

## Installation

```bash
pip install agentecs-viz
```

This installs `agentecs` as a dependency automatically.

## Quick Start

### Demo Mode

Run with mock data to explore the interface:

```bash
agentecs-viz serve --mock
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Run Example with Visualization

```bash
# Install viz if not already installed
pip install agentecs-viz

# Run the task dispatch example with visualization (from agentecs-examples repo)
python examples/task_dispatch/main.py --viz
```

### Visualize Your World

Connect to an existing AgentECS world:

```python
# myapp/world.py
from agentecs import World
from agentecs_viz.sources import LocalWorldSource

world = World()
# ... set up your world ...

# Export for the visualizer
def get_world_source():
    return LocalWorldSource(world, tick_interval=0.5)
```

Then run:

```bash
agentecs-viz serve -m myapp.world
```

!!! note "Automatic Ticking"
    `LocalWorldSource` controls the World automatically—it calls `tick_async()` at the configured interval. No manual tick notification needed.

## Features

### Semantic Zoom Levels

The Petri Dish canvas automatically adapts based on zoom level:

| Level | Scale | View |
|-------|-------|------|
| **MICRO** | > 2.5× | Focal entity with full component details |
| **DETAIL** | 0.8–2.5× | Individual entities as colored circles |
| **MESO** | 0.3–0.8× | Clustered dots with count labels |
| **MACRO** | < 0.3× | Density heat map |

### Timeline & Replay

Record sessions and replay them later:

```bash
# Record while serving
agentecs-viz serve -m myapp.world --record-to trace.jsonl

# Replay a recording
agentecs-viz replay trace.jsonl
```

The timeline bar at the bottom allows scrubbing through history.

### Tabs

- **Petri Dish** – Interactive canvas with pan/zoom
- **List** – Sortable entity table with expandable details
- **Data** – Statistics, archetype distribution, CSV/JSON export
- **Timeline** – Entity lifecycle swimlanes
- **Archetypes** – Component pattern groupings
- **Chat** – Task/agent interaction panel

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`–`6` | Switch tabs |
| `Space` | Play/pause |
| `→` | Step forward (when paused) |
| `+` / `-` | Zoom in/out |

## Next Steps

- [Architecture](architecture.md) – System design and protocols
- [CLI Reference](cli.md) – Command options
- [Extending](extending.md) – Custom sources and theming
