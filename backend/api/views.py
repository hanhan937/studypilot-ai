
"""
StudyPilot AI REST API views.

Endpoints:
    GET  /api/health/
    GET  /api/config/
    GET  /api/csrf/
    GET  /api/tasks/
    GET  /api/plans/
    POST /api/plans/generate/
    POST /api/plans/<plan_id>/reschedule/

Chat is handled separately in api/chat_view.py.
"""

import logging

from django.conf import settings
from django.middleware.csrf import get_token

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from agent import task_service
from agent.planning_service import generate_study_plan
from agent.rescheduling_service import reschedule_study_plan

from api.models import StudyPlan

from .csrf_protection import require_csrf
from .guest_session import get_guest_session_key


logger = logging.getLogger(__name__)


# ---------- Health ----------

@api_view(["GET"])
def health(request):
    return Response({
        "status": "ok",
        "message": "StudyPilot API is running",
    })


# ---------- Configuration ----------

@api_view(["GET"])
def config(request):
    return Response({
        "mock_ai": settings.MOCK_AI,
    })


# ---------- CSRF Token ----------

@api_view(["GET"])
def csrf_token(request):
    """Initialize the guest session and return a CSRF token."""

    get_guest_session_key(request)

    return Response({
        "csrfToken": get_token(request),
    })


# ---------- Tasks ----------

@api_view(["GET"])
def tasks(request):
    """Return tasks belonging to the current visitor."""

    session_key = get_guest_session_key(request)

    results = task_service.list_tasks(
        session_key=session_key,
    )

    return Response({
        "tasks": results,
    })


# ---------- Study Plan Generation ----------

@require_csrf
@api_view(["POST"])
def generate_plan(request):
    """Generate a study plan for the current visitor."""

    session_key = get_guest_session_key(request)

    try:
        result = generate_study_plan(
            goal=request.data.get("goal"),
            days=request.data.get("days"),
            daily_minutes=request.data.get("daily_minutes"),
            session_key=session_key,
        )

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )

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


# ---------- Saved Study Plans ----------

@api_view(["GET"])
def plans(request):
    """Return only the current visitor's study plans and tasks."""

    session_key = get_guest_session_key(request)

    results = []

    owned_plans = (
        StudyPlan.objects
        .filter(session_key=session_key)
        .prefetch_related("tasks")
        .order_by("-created_at", "-id")
    )

    for plan in owned_plans:

        plan_tasks = sorted(
            (
                task
                for task in plan.tasks.all()
                if task.session_key == session_key
            ),
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
                        if task.scheduled_date
                        else None
                    ),
                    "estimated_minutes": task.estimated_minutes,
                    "completed": task.completed,
                }
                for task in plan_tasks
            ],
        })

    return Response({
        "plans": results,
    })


# ---------- Adaptive Rescheduling ----------

@require_csrf
@api_view(["POST"])
def reschedule_plan(request, plan_id):
    """Reschedule only a plan owned by the current visitor."""

    session_key = get_guest_session_key(request)

    try:
        result = reschedule_study_plan(
            plan_id,
            session_key=session_key,
        )

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
