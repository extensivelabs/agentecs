# Extending

## Custom WorldStateSource

Implement the protocol to visualize any data source:

```python
from collections.abc import AsyncIterator
from agentecs_viz.protocol import WorldStateSource, WorldEvent, TickEvent
from agentecs_viz.snapshot import WorldSnapshot, EntitySnapshot, ComponentSnapshot

class MyCustomSource:
    def __init__(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True
        # Initialize your data source

    async def disconnect(self) -> None:
        self._connected = False
        # Clean up resources

    async def get_snapshot(self) -> WorldSnapshot:
        # Build snapshot from your data
        entities = [
            EntitySnapshot(
                id=1,
                components=[
                    ComponentSnapshot(
                        type_name="myapp.Position",
                        type_short="Position",
                        data={"x": 10.0, "y": 20.0}
                    )
                ]
            )
        ]
        return WorldSnapshot(tick=0, entity_count=len(entities), entities=entities)

    async def subscribe_events(self) -> AsyncIterator[WorldEvent]:
        # Yield events as they occur
        while self._connected:
            snapshot = await self.get_snapshot()
            yield TickEvent(snapshot)
            await asyncio.sleep(1.0)

    async def send_command(self, command: str, **kwargs) -> None:
        if command == "pause":
            # Handle pause
            pass
```

## History Stores

### InMemoryHistoryStore

Bounded buffer for development:

```python
from agentecs_viz.history import InMemoryHistoryStore

store = InMemoryHistoryStore(max_ticks=1000)
```

### FileHistoryStore

Persistent JSON Lines storage:

```python
from pathlib import Path
from agentecs_viz.history import FileHistoryStore

# Write mode
with FileHistoryStore(Path("trace.jsonl"), mode="w") as store:
    store.record_tick(tick_record)

# Read mode
store = FileHistoryStore(Path("trace.jsonl"), mode="r")
snapshot = store.get_snapshot(tick=42)
```

### HistoryCapturingSource

Wrap any source to add recording and replay:

```python
from agentecs_viz.history import HistoryCapturingSource, InMemoryHistoryStore
from agentecs_viz.sources import LocalWorldSource

source = LocalWorldSource(world, tick_interval=0.5)
store = InMemoryHistoryStore(max_ticks=500)
capturing = HistoryCapturingSource(source, store)

# Now capturing.supports_replay == True
# Use with create_app() for visualization with history
```

## Theming

The frontend uses CSS custom properties. Override in your own stylesheet:

```css
:root {
  /* Background colors */
  --color-bg-primary: #0f0f1a;
  --color-bg-secondary: #1a1a2e;
  --color-bg-tertiary: #2a2a3e;

  /* Text colors */
  --color-text-primary: #f0f0f0;
  --color-text-secondary: #a0a0b0;
  --color-text-muted: #606070;

  /* Accent */
  --color-accent: #6366f1;

  /* Status colors */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
}
```

## Adding Tabs

Tabs are Svelte components in `frontend/src/lib/` (in the agentecs-viz repository). Pattern:

```svelte
<!-- MyTab.svelte -->
<script lang="ts">
  import { world } from "./world.svelte";

  // Access world state via the store
  const entities = $derived(world.entities);
</script>

<div class="p-4">
  <h2>My Custom Tab</h2>
  {#each entities as entity}
    <div>{entity.id}: {entity.archetype.join(", ")}</div>
  {/each}
</div>
```

Register in `App.svelte`:

```svelte
<TabBar tabs={[
  { id: "petri", label: "Petri Dish" },
  { id: "mytab", label: "My Tab" },  // Add here
  // ...
]} />

{#if activeTab === "mytab"}
  <MyTab />
{/if}
```

## WebSocket API

Connect directly for custom integrations:

```typescript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "tick") {
    console.log("Tick:", msg.snapshot.tick);
  }
};

// Send commands
ws.send(JSON.stringify({ command: "pause" }));
ws.send(JSON.stringify({ command: "seek", tick: 100 }));
```
