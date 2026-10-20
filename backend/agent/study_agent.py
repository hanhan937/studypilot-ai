
from agents import Agent, Runner

from .context import StudyAgentContext
from .instructions import STUDYPILOT_INSTRUCTIONS
from .tools import (
    create_task,
    list_tasks,
    complete_task,
    get_progress,
)


study_agent = Agent[StudyAgentContext](
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


async def generate_reply(
    message: str,
    *,
    session_key: str,
) -> str:
    """Run the AI Agent using the current visitor's context."""

    session_key = session_key.strip()
    if not session_key:
        raise ValueError("A valid session key is required.")

    context = StudyAgentContext(session_key=session_key)

    result = await Runner.run(
        study_agent,
        message,
        context=context,
    )

    return str(result.final_output)
