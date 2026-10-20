
"""
StudyPilot AI Chat API.

POST /api/chat/

MOCK_AI=true:
    Demo Mode uses deterministic commands.

MOCK_AI=false:
    Real Mode uses the OpenAI Agents SDK.

All operations use the current visitor's Django session.

Response:
    {"reply": "...", "mode": "demo" | "real"}
"""

import logging

from django.conf import settings

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from agent.demo_commands import handle_demo_command
from agent.exceptions import (
    AgentConfigError,
    AgentServiceError,
    AgentTimeoutError,
)
from agent.service import run_study_agent

from .csrf_protection import require_csrf
from .guest_session import get_guest_session_key


logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000


def _validate_message(data):
    """Validate incoming chat messages."""

    message = (
        data.get("message")
        if isinstance(data, dict)
        else None
    )

    if not isinstance(message, str) or not message.strip():
        return None, "Please provide a non-empty 'message'."

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:
        return None, (
            f"Message must be at most {MAX_MESSAGE_LENGTH} characters."
        )

    return message, None


@require_csrf
@api_view(["POST"])
def chat(request):
    """Handle a chat request for the current guest session."""

    message, error = _validate_message(request.data)

    if error:
        return Response(
            {"error": error},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_key = get_guest_session_key(request)

    # ---------- Demo Mode ----------

    if settings.MOCK_AI:
        try:
            reply = handle_demo_command(
                message,
                session_key=session_key,
            )

        except Exception as exc:
            logger.error(
                "Demo command crashed (%s)",
                type(exc).__name__,
            )

            return Response(
                {
                    "error": "The demo command failed unexpectedly.",
                    "mode": "demo",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "reply": reply,
            "mode": "demo",
        })

    # ---------- Real AI Mode ----------

    try:
        reply = run_study_agent(
            message,
            session_key=session_key,
        )

    except AgentConfigError:
        return Response(
            {
                "error": "The AI service is not configured on the server.",
                "mode": "real",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except AgentTimeoutError:
        return Response(
            {
                "error": (
                    "The AI took too long to respond. "
                    "Please try again."
                ),
                "mode": "real",
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    except AgentServiceError:
        return Response(
            {
                "error": (
                    "The AI service is unavailable right now. "
                    "Please try again later."
                ),
                "mode": "real",
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({
        "reply": reply,
        "mode": "real",
    })
