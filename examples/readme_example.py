"""AgentECS Example: Agents Processing a Shared Task List.

Two systems run in parallel:
1. Spawner: creates new agents when tasks outnumber agents
2. Processor: each agent completes one task per tick

Agents share the same TaskList object - modifications are immediately
visible to all agents within the same tick.
"""

from dataclasses import dataclass, field
from enum import Enum

from agentecs import ScopedAccess, World, component, system


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass
class Task:
    description: str
    status: TaskStatus = TaskStatus.PENDING


@component
@dataclass
class TaskList:
    tasks: list[Task] = field(default_factory=list)


@system(reads=(TaskList,), writes=(TaskList,))
def spawn_agents(world: ScopedAccess) -> None:
    """Spawn agents when pending tasks exceed agent count."""
    agents = list(world(TaskList))
    if not agents:
        return

    _, task_list = agents[0]
    pending = sum(1 for t in task_list.tasks if t.status == TaskStatus.PENDING)

    if pending > len(agents):
        world.spawn(task_list)


@system(reads=(TaskList,), writes=(TaskList,))
def process_tasks(world: ScopedAccess) -> None:
    """Each agent completes one pending task."""
    for entity, task_list in world(TaskList):
        for task in task_list.tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.COMPLETED
                print(f"Agent {entity.index}: {task.description}")
                world[entity, TaskList] = task_list
                break


def main() -> None:
    world = World()
    world.register_system(spawn_agents)
    world.register_system(process_tasks)

    tasks = TaskList(tasks=[Task(f"Task-{i}") for i in range(1, 5)])
    world.spawn(tasks)

    for tick in range(1, 4):
        print(f"--- Tick {tick} ---")
        world.tick()
        agents = list(world.query(TaskList))
        _, tl = agents[0]
        done = sum(1 for t in tl.tasks if t.status == TaskStatus.COMPLETED)
        print(f"    ({len(agents)} agents, {done}/4 done)")


if __name__ == "__main__":
    main()
