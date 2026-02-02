from dataclasses import dataclass, field
from enum import Enum

from agentecs import ScopedAccess, World, component, system


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Task:
    description: str
    status: TaskStatus


@component
@dataclass
class TaskList:
    """Wrapper component for multiple tasks per entity.

    ECS uses one component per type per entity. To have multiple tasks,
    use a wrapper component containing a list.
    """

    tasks: list[Task] = field(default_factory=list)


@system(reads=(TaskList,), writes=(TaskList,))
def agent_splitter(world: ScopedAccess) -> None:
    """Split agents with too many pending tasks."""
    for entity, task_list in world(TaskList):
        pending = [t for t in task_list.tasks if t.status == TaskStatus.PENDING]
        print(f"Agent {entity} has {len(pending)} pending tasks.")

        if len(pending) > 3:
            # Split: keep first half, spawn new agent with second half
            mid = len(task_list.tasks) // 2
            first_half = task_list.tasks[:mid]
            second_half = task_list.tasks[mid:]

            world[entity, TaskList] = TaskList(tasks=first_half)
            new_entity = world.spawn(TaskList(tasks=second_half))
            print(f"Agent {entity} split into new agent {new_entity}.")


@system(reads=(TaskList,), writes=(TaskList,))
def task_progressor(world: ScopedAccess) -> None:
    """Progress tasks through their lifecycle."""
    for entity, task_list in world(TaskList):
        updated_tasks = []
        for task in task_list.tasks:
            if task.status == TaskStatus.PENDING:
                updated_tasks.append(Task(task.description, TaskStatus.IN_PROGRESS))
            elif task.status == TaskStatus.IN_PROGRESS:
                updated_tasks.append(Task(task.description, TaskStatus.COMPLETED))
            else:
                updated_tasks.append(task)
        world[entity, TaskList] = TaskList(tasks=updated_tasks)
        print(f"Agent {entity}: progressed {len(task_list.tasks)} tasks.")


def main() -> None:
    world = World()
    world.register_system(agent_splitter)
    world.register_system(task_progressor)

    # Spawn agent with multiple tasks via TaskList wrapper
    world.spawn(
        TaskList(
            tasks=[
                Task("Collect data", TaskStatus.PENDING),
                Task("Analyze data", TaskStatus.PENDING),
                Task("Generate report", TaskStatus.PENDING),
                Task("Review findings", TaskStatus.PENDING),
            ]
        )
    )

    print(f"Initial agents: {len(list(world.query(TaskList)))}")
    world.tick()
    print(f"After tick 1: {len(list(world.query(TaskList)))} agents")
    world.tick()
    print(f"After tick 2: {len(list(world.query(TaskList)))} agents")


if __name__ == "__main__":
    main()
