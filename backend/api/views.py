
import asyncio
import logging
import os

from agent.planning_service import generate_study_plan
from agent.rescheduling_service import reschedule_study_plan
from api.models import StudyPlan

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



@api_view(["POST"])
def generate_plan(request):
    """Generate and save a study plan."""
    try:
        result = generate_study_plan(
            goal=request.data.get("goal"),
            days=request.data.get("days"),
            daily_minutes=request.data.get("daily_minutes"),
        )
        return Response(result, status=status.HTTP_201_CREATED)

    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        logger.exception("Failed to generate study plan")
        return Response(
            {"error": "Failed to generate study plan."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def plans(request):
    """Return all study plans with their tasks."""
    results = []

    for plan in StudyPlan.objects.prefetch_related("tasks").order_by(
        "-created_at", "-id"
    ):
        plan_tasks = sorted(
            plan.tasks.all(),
            key=lambda task: (
                task.scheduled_date or plan.start_date,
                task.id,
            ),
        )

        results.append({
            "id": plan.id,
            "goal": plan.goal,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "daily_minutes": plan.daily_minutes,
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "topic": task.topic,
                    "scheduled_date": (
                        task.scheduled_date.isoformat()
                        if task.scheduled_date else None
                    ),
                    "estimated_minutes": task.estimated_minutes,
                    "completed": task.completed,
                }
                for task in plan_tasks
            ],
        })

    return Response({"plans": results})


@api_view(["POST"])
def reschedule_plan(request, plan_id):
    """Reschedule overdue, unfinished study tasks."""
    try:
        result = reschedule_study_plan(plan_id)
        return Response(result)

    except StudyPlan.DoesNotExist:
        return Response(
            {"error": "Study plan not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        logger.exception("Failed to reschedule study plan")
        return Response(
            {"error": "Failed to reschedule study plan."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


