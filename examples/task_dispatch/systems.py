"""ECS systems for task dispatch."""

from __future__ import annotations

import os

from components import AgentState, Task, TaskQueue, TaskStatus
from llm_utils import get_llm_client
from models import AgentResponse, ResponseType
from pydantic import BaseModel

from agentecs import ScopedAccess, system
from agentecs.adapters import Message

# Configuration
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))


@system()
async def task_assignment_system(world: ScopedAccess) -> None:
    """Spawn agents for unassigned tasks."""
    import asyncio

    queue = world.singleton(TaskQueue)
    if not queue or not queue.tasks:
        return

    client = get_llm_client()

    class SystemPrompt(BaseModel):
        prompt: str

    # Collect unassigned tasks and build LLM calls
    unassigned_tasks = [t for t in queue.tasks if t.status == TaskStatus.UNASSIGNED]
    if not unassigned_tasks:
        return

    async def generate_system_prompt(task: Task) -> tuple[Task, str]:
        """Generate system prompt for a task."""
        meta_prompt = (
            "Create a specialized system prompt for an AI agent that needs to "
            f"complete this task:\n\nTask: {task.description}\n\n"
            "The system prompt should:\n"
            "1. Define the agent's role and expertise relevant to this task\n"
            "2. Provide guidance on how to approach the task\n"
            "3. Be concise but comprehensive (1-3 paragraphs)\n\n"
            "Return only the system prompt text, nothing else."
        )
        response = await client.call_async(
            messages=[Message.user(meta_prompt)],
            response_model=SystemPrompt,
            max_tokens=500,
        )
        return task, response.prompt

    # Run all LLM calls in parallel
    results = await asyncio.gather(*[generate_system_prompt(t) for t in unassigned_tasks])

    for task, system_prompt in results:
        task.status = TaskStatus.IN_PROGRESS
        world.spawn(
            AgentState(system_prompt=system_prompt, conversation_history=[]),
            task,
        )
        queue.tasks.remove(task)
        print(f"Spawned agent for task: {task.id[:8]}... ({task.description[:50]}...)")

    world.update_singleton(queue)


@system()
async def agent_processing_system(world: ScopedAccess) -> None:
    """Process active agents with tasks."""
    import asyncio

    client = get_llm_client()

    # Collect agents that need processing
    agents_to_process = []
    for entity, agent_state, task in world(AgentState, Task):
        if task.status != TaskStatus.IN_PROGRESS:
            continue

        if agent_state.iteration_count >= MAX_ITERATIONS:
            print(f"Agent {entity.index} hit max iterations ({MAX_ITERATIONS}), completing task")
            last_thought = (
                agent_state.conversation_history[-1]["content"]
                if agent_state.conversation_history
                else "none"
            )
            task.result = (
                f"Task reached maximum iterations ({MAX_ITERATIONS}) "
                f"without completion. Last reasoning: {last_thought}"
            )
            task.status = TaskStatus.COMPLETED
            world[entity, Task] = task
            continue

        agents_to_process.append((entity, agent_state, task))

    if not agents_to_process:
        return

    async def process_agent(entity, agent_state, task):
        """Process single agent with LLM call."""
        messages = [Message.user(f"Task: {task.description}")]

        for msg in agent_state.conversation_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                messages.append(Message.user(content))
            elif role == "assistant":
                messages.append(Message.assistant(content))
            elif role == "system":
                messages.append(Message.system(content))

        if task.user_response:
            messages.append(Message.user(task.user_response))

        full_messages = [Message.system(agent_state.system_prompt)] + messages
        response = await client.call_async(full_messages, response_model=AgentResponse)
        return entity, agent_state, task, response

    # Run all LLM calls in parallel
    results = await asyncio.gather(*[process_agent(e, a, t) for e, a, t in agents_to_process])

    for entity, agent_state, task, response in results:
        agent_state.iteration_count += 1

        if task.user_response:
            agent_state.conversation_history.append({"role": "user", "content": task.user_response})
            task.user_response = None

        if response.response_type == ResponseType.DEEP_THOUGHT:
            agent_state.conversation_history.append(
                {
                    "role": "assistant",
                    "content": f"[Thinking] {response.reasoning}\n{response.message}",
                }
            )
            task.status = TaskStatus.IN_PROGRESS
            print(
                f"Agent {entity.index} (iter {agent_state.iteration_count}) "
                f"thinking: {response.message[:60]}..."
            )

        elif response.response_type == ResponseType.ASK_USER:
            agent_state.conversation_history.append(
                {"role": "assistant", "content": response.message}
            )
            task.user_query = response.message
            task.status = TaskStatus.WAITING_FOR_INPUT
            print(f"Agent {entity.index} asks: {response.message}")

        elif response.response_type == ResponseType.FINAL_ANSWER:
            agent_state.conversation_history.append(
                {"role": "assistant", "content": response.message}
            )
            task.result = response.message
            task.status = TaskStatus.COMPLETED
            print(f"Agent {entity.index} completed: {response.message[:60]}...")

        world[entity, AgentState] = agent_state
        world[entity, Task] = task


@system()
def agent_cleanup_system(world: ScopedAccess) -> None:
    """Destroy agents whose tasks are complete."""
    to_destroy = []

    for entity, _agent_state, task in world(AgentState, Task):
        if task.status == TaskStatus.COMPLETED:
            to_destroy.append((entity, task))

    for entity, task in to_destroy:
        print(f"Cleaning up agent {entity.index} (task {task.id[:8]}... completed)")
        world.destroy(entity)
