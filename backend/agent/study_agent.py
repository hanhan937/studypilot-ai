
from agents import Agent, Runner

from .instructions import STUDYPILOT_INSTRUCTIONS
from .tools import (
    create_task,
    list_tasks,
    complete_task,
    get_progress,
)


study_agent = Agent(
    name="StudyPilot AI",
    instructions=STUDYPILOT_INSTRUCTIONS,
    model="gpt-4.1-mini",
    tools=[
        create_task,
        list_tasks,
        complete_task,
        get_progress,
    ],
)


async def generate_reply(message: str) -> str:
    result = await Runner.run(study_agent, message)
    return str(result.final_output)
