
"""
Run the StudyPilot AI agent.

Demo Mode uses deterministic commands in demo_commands.py.
Real Mode uses the OpenAI Agents SDK.

The Django backend supplies a trusted session_key,
which is passed to Agent Tools through RunContext.
"""

import asyncio
import logging

import openai
from agents import Agent, OpenAIResponsesModel, RunConfig, Runner
from agents.exceptions import AgentsException
from django.conf import settings
from openai import AsyncOpenAI

from . import task_service
from .context import StudyAgentContext
from .exceptions import (
    AgentConfigError,
    AgentServiceError,
    AgentTimeoutError,
)
from .instructions import STUDYPILOT_INSTRUCTIONS
from .mock import get_mock_reply
from .tools import (
    create_task,
    list_tasks,
    complete_task,
    get_progress,
)

logger = logging.getLogger(__name__)


def build_agent(client: AsyncOpenAI) -> Agent[StudyAgentContext]:
    """Build an agent whose tools use trusted session context."""
    return Agent[StudyAgentContext](
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


async def _run(message: str, *, session_key: str) -> str:
    """Execute the real agent for one guest session."""
    api_key = settings.OPENAI_API_KEY

    if not api_key:
        raise AgentConfigError("OPENAI_API_KEY is not set.")

    timeout = settings.OPENAI_TIMEOUT_SECONDS

    context = StudyAgentContext(
        session_key=session_key,
    )

    # Create a fresh client for each request.
    client = AsyncOpenAI(
        api_key=api_key,
        timeout=timeout,
        max_retries=1,
    )

    try:
        agent = build_agent(client)

        result = await asyncio.wait_for(
            Runner.run(
                agent,
                message,
                context=context,
                run_config=RunConfig(
                    tracing_disabled=True,
                ),
            ),
            timeout=timeout,
        )

    finally:
        await client.close()

    reply = result.final_output

    if not isinstance(reply, str) or not reply.strip():
        raise AgentServiceError(
            "The agent returned an empty response."
        )

    return reply.strip()


def run_study_agent(
    message: str,
    *,
    session_key: str,
) -> str:
    """Return an agent reply scoped to the current visitor."""

    # Validate before any agent or tool is used.
    session_key = task_service.validate_session_key(
        session_key
    )

    # Keep the previous mock behavior for direct service calls.
    # The HTTP Demo Mode entry point remains chat_view.py.
    if settings.MOCK_AI:
        return get_mock_reply(message)

    try:
        return asyncio.run(
            _run(
                message,
                session_key=session_key,
            )
        )

    except (
        AgentConfigError,
        AgentServiceError,
        AgentTimeoutError,
    ):
        raise

    except (
        asyncio.TimeoutError,
        openai.APITimeoutError,
    ) as exc:
        logger.warning(
            "Agent call timed out (%s)",
            type(exc).__name__,
        )

        raise AgentTimeoutError(
            "The AI took too long to respond."
        ) from exc

    except (
        openai.OpenAIError,
        AgentsException,
    ) as exc:
        logger.error(
            "Agent call failed (%s)",
            type(exc).__name__,
        )

        raise AgentServiceError(
            "The AI service request failed."
        ) from exc

    except Exception as exc:
        logger.error(
            "Unexpected agent error (%s)",
            type(exc).__name__,
        )

        raise AgentServiceError(
            "Unexpected error while running the agent."
        ) from exc
