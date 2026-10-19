"""
Runs the StudyPilot agent.

The web layer calls `run_study_agent(message)` and gets back plain text, or one of the
errors from `agent.exceptions`. Everything OpenAI-specific lives in this file.
"""
import asyncio
import logging

import openai
from agents import Agent, OpenAIResponsesModel, RunConfig, Runner
from agents.exceptions import AgentsException
from django.conf import settings
from openai import AsyncOpenAI

from .exceptions import AgentConfigError, AgentServiceError, AgentTimeoutError
from .instructions import STUDYPILOT_INSTRUCTIONS
from .mock import get_mock_reply

from .tools import (
    create_task,
    list_tasks,
    complete_task,
    get_progress,
)

logger = logging.getLogger(__name__)




def build_agent(client: AsyncOpenAI) -> Agent:
    return Agent(
        name="StudyPilot",
        instructions=STUDYPILOT_INSTRUCTIONS,
        model=OpenAIResponsesModel(
            model=settings.OPENAI_MODEL,
            openai_client=client,
        ),
        tools=[
            create_task,
            list_tasks,
            complete_task,
            get_progress,
        ],
    )



async def _run(message: str) -> str:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise AgentConfigError("OPENAI_API_KEY is not set.")

    timeout = settings.OPENAI_TIMEOUT_SECONDS

    # A fresh client per request: each request runs in its own event loop (see run_study_agent),
    # and an async HTTP client must not be shared between event loops.
    client = AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=1)
    try:
        agent = build_agent(client)
        result = await asyncio.wait_for(
            Runner.run(
                agent,
                message,
                # Tracing would upload run data to OpenAI's dashboard; keep it off for now.
                run_config=RunConfig(tracing_disabled=True),
            ),
            timeout=timeout,
        )
    finally:
        await client.close()

    reply = result.final_output
    if not isinstance(reply, str) or not reply.strip():
        raise AgentServiceError("The agent returned an empty response.")
    return reply.strip()


def run_study_agent(message: str) -> str:
    """Send the user's message to the StudyPilot agent and return its text reply."""
    # Mock Mode: answer locally. This returns before any OpenAI client or Runner is created.
    if settings.MOCK_AI:
        return get_mock_reply(message)

    try:
        return asyncio.run(_run(message))
    except (AgentConfigError, AgentServiceError, AgentTimeoutError):
        raise
    except (asyncio.TimeoutError, openai.APITimeoutError) as exc:
        # APITimeoutError must be checked before the generic OpenAI errors below.
        logger.warning("Agent call timed out (%s)", type(exc).__name__)
        raise AgentTimeoutError("The AI took too long to respond.") from exc
    except (openai.OpenAIError, AgentsException) as exc:
        # Log only the error type: provider messages can contain parts of the API key.
        logger.error("Agent call failed (%s)", type(exc).__name__)
        raise AgentServiceError("The AI service request failed.") from exc
    except Exception as exc:  # last-resort safety net so the API returns clean JSON
        logger.error("Unexpected agent error (%s)", type(exc).__name__)
        raise AgentServiceError("Unexpected error while running the agent.") from exc
