# CLI Reference

## agentecs-viz serve

Start the visualization server.

```bash
agentecs-viz serve [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-m, --world-module` | – | Python module path (e.g., `myapp.world`) |
| `--mock` | – | Use MockWorldSource for demo |
| `-p, --port` | 8000 | Server port |
| `--host` | 127.0.0.1 | Server host |
| `--no-frontend` | – | API only, don't serve static files |
| `--record-to` | – | Record trace to file while serving |
| `-v, --verbose` | – | Enable debug logging |

### Examples

```bash
# Demo with mock data
agentecs-viz serve --mock

# Load from Python module
agentecs-viz serve -m myapp.world

# Custom port
agentecs-viz serve --port 3000

# Record while serving
agentecs-viz serve -m myapp.world --record-to trace.jsonl
```

### Module Loading

When using `-m`, the CLI looks for (in order):

1. `get_world_source()` function → returns WorldStateSource
2. `world_source` attribute → WorldStateSource instance
3. `world` attribute → wrapped with LocalWorldSource

```python
# myapp/world.py

# Option 1: Factory function (recommended)
def get_world_source():
    world = create_my_world()
    return LocalWorldSource(world)

# Option 2: Direct attribute
world_source = LocalWorldSource(my_world)

# Option 3: Just the world
world = World()  # CLI wraps it automatically
```

---

## agentecs-viz record

Record a trace file without serving the UI.

```bash
agentecs-viz record -o FILE [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | **required** | Output file path (.jsonl) |
| `-m, --world-module` | – | Python module path |
| `--mock` | – | Use MockWorldSource |
| `--ticks` | – | Number of ticks to record |
| `--duration` | – | Max duration in seconds |
| `--tick-interval` | 0.5 | Seconds between ticks |
| `-v, --verbose` | – | Enable debug logging |

### Examples

```bash
# Record mock until Ctrl+C
agentecs-viz record -o trace.jsonl --mock

# Record from module
agentecs-viz record -m myapp.world -o trace.jsonl

# Record exactly 100 ticks
agentecs-viz record --mock -o trace.jsonl --ticks 100

# Record for 30 seconds
agentecs-viz record --mock -o trace.jsonl --duration 30
```

Press `Ctrl+C` to stop recording.

---

## agentecs-viz replay

Replay a recorded trace file.

```bash
agentecs-viz replay FILE [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `FILE` | **required** | Trace file to replay (.jsonl) |
| `-p, --port` | 8000 | Server port |
| `--host` | 127.0.0.1 | Server host |
| `--speed` | 1.0 | Playback speed multiplier |
| `--no-frontend` | – | API only |
| `-v, --verbose` | – | Enable debug logging |

### Examples

```bash
# Normal replay
agentecs-viz replay trace.jsonl

# 2x speed
agentecs-viz replay trace.jsonl --speed 2.0

# Custom port
agentecs-viz replay trace.jsonl --port 3001
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_WS_PORT` | Override WebSocket port in frontend build |

---

## Trace File Format

Traces use JSON Lines format (`.jsonl`):

```json
{"tick": 0, "timestamp": 1704067200.0, "snapshot": {...}, "events": []}
{"tick": 1, "timestamp": 1704067200.5, "snapshot": {...}, "events": []}
```

Each line is a `TickRecord` with:

- `tick` – Tick number
- `timestamp` – Unix timestamp
- `snapshot` – Full WorldSnapshot
- `events` – List of events (currently unused)
