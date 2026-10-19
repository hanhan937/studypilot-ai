
import asyncio
import logging
import os

from agent import task_service
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from agent.study_agent import generate_reply

logger = logging.getLogger(__name__)


@api_view(["GET"])
def health(request):
    return Response({
        "status": "ok",
        "message": "StudyPilot API is running",
    })


@api_view(["POST"])
def chat(request):
    message = request.data.get("message")

    if not isinstance(message, str) or not message.strip():
        return Response(
            {"error": "Please enter a valid message."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(message) > 4000:
        return Response(
            {"error": "Message is too long."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not os.getenv("OPENAI_API_KEY"):
        return Response(
            {"error": "OpenAI API key is not configured."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        reply = asyncio.run(generate_reply(message.strip()))
        return Response({"reply": reply})

    except Exception:
        logger.exception("StudyPilot chat request failed")
        return Response(
            {"error": "AI service is currently unavailable."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
        

@api_view(["GET"])
def tasks(request):
    """Return all saved study tasks."""
    results = task_service.list_tasks()
    return Response({"tasks": results})
