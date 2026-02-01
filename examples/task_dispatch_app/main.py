"""CLI entry point for task dispatch example.

Usage:
    python main.py              # Interactive mode
    python main.py --headless   # Auto-respond to agent questions
    python main.py --viz        # Start visualization server
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from components import AgentState, Task, TaskStatus
from world import EXAMPLE_TASKS, create_world


async def run_interactive(world, max_ticks: int = 20) -> None:
    """Run with user interaction."""
    for tick in range(max_ticks):
        print(f"\n--- Tick {tick + 1} ---")
        await world.tick_async()

        # Handle agents waiting for input
        for entity, _state, task in world.query(AgentState, Task):
            if task.status == TaskStatus.WAITING_FOR_INPUT:
                print(f"\nAgent {entity.index} asks: {task.user_query}")
                try:
                    response = input("Your answer: ")
                except EOFError:
                    response = "skip"
                task.user_response = response
                task.status = TaskStatus.IN_PROGRESS
                world.set(entity, task)

        # Check if done
        if sum(1 for _ in world.query(AgentState)) == 0:
            print("\nAll tasks completed!")
            break


async def run_headless(world, max_ticks: int = 10) -> None:
    """Run without interaction - auto-respond to agents."""
    for tick in range(max_ticks):
        print(f"Tick {tick + 1}...", end=" ", flush=True)
        await world.tick_async()

        for entity, _state, task in world.query(AgentState, Task):
            if task.status == TaskStatus.WAITING_FOR_INPUT:
                task.user_response = "Please proceed with your best judgment."
                task.status = TaskStatus.IN_PROGRESS
                world.set(entity, task)

        active = sum(1 for _ in world.query(AgentState))
        print(f"{active} agents")
        if active == 0:
            break


def run_viz(world, port: int = 8000) -> None:
    """Start visualization server."""
    import uvicorn
    from agentecs_viz.cli import get_frontend_dir
    from agentecs_viz.history import HistoryCapturingSource
    from agentecs_viz.server import create_app
    from agentecs_viz.sources.local import LocalWorldSource
    from fastapi.staticfiles import StaticFiles

    source = HistoryCapturingSource(LocalWorldSource(world))
    app = create_app(source)

    # Mount frontend static files
    try:
        frontend_dir = get_frontend_dir()
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    except FileNotFoundError:
        print("Warning: Frontend not built. Run 'npm run build' in viz/frontend/")

    print(f"\nStarting visualization at http://127.0.0.1:{port}")
    print(f"API docs: http://127.0.0.1:{port}/docs\n")
    uvicorn.run(app, host="127.0.0.1", port=port)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="task-dispatch",
        description="Task Dispatch - AgentECS example with LLM agents",
    )
    parser.add_argument("--headless", action="store_true", help="Auto-respond mode")
    parser.add_argument("--viz", action="store_true", help="Start visualization server")
    parser.add_argument("--port", type=int, default=8000, help="Viz server port")
    parser.add_argument("--ticks", type=int, default=20, help="Max ticks to run")
    parser.add_argument("--tasks", nargs="+", help="Custom task descriptions")

    args = parser.parse_args(argv)
    tasks = args.tasks or EXAMPLE_TASKS
    world = create_world(tasks)

    print(f"\nTask Dispatch Example ({len(tasks)} tasks)")
    for i, t in enumerate(tasks, 1):
        print(f"  {i}. {t}")
    print()

    if args.viz:
        run_viz(world, args.port)
    elif args.headless:
        asyncio.run(run_headless(world, args.ticks))
    else:
        asyncio.run(run_interactive(world, args.ticks))

    return 0


if __name__ == "__main__":
    sys.exit(main())
