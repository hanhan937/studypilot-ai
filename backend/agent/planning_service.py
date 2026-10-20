
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import StudyPlan, Task
from agent.task_service import validate_session_key


# Demo Mode: fixed topics for coding interview preparation.
CODING_TOPICS = [
    "Arrays and Hash Maps",
    "Two Pointers",
    "Sliding Window",
    "Binary Search",
    "Linked Lists",
    "Trees and Graphs",
    "Dynamic Programming",
    "Review and Mock Interview",
]


def generate_study_plan(
    goal: str,
    days: int,
    daily_minutes: int,
    *,
    session_key: str,
) -> dict:
    """Create a study plan belonging to one guest session."""

    # Require a session identity for every new plan.
    session_key = validate_session_key(session_key)

    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("Goal cannot be empty.")

    if len(goal.strip()) > 500:
        raise ValueError("Goal is too long.")

    if (
        not isinstance(days, int)
        or isinstance(days, bool)
        or not 1 <= days <= 30
    ):
        raise ValueError("Days must be between 1 and 30.")

    if (
        not isinstance(daily_minutes, int)
        or isinstance(daily_minutes, bool)
        or not 15 <= daily_minutes <= 480
    ):
        raise ValueError("Daily minutes must be between 15 and 480.")

    goal = goal.strip()
    start_date = timezone.localdate()
    end_date = start_date + timedelta(days=days - 1)

    # Both the plan and its tasks are saved together.
    with transaction.atomic():
        plan = StudyPlan.objects.create(
            session_key=session_key,
            goal=goal,
            start_date=start_date,
            end_date=end_date,
            daily_minutes=daily_minutes,
        )

        tasks = []

        for day in range(days):
            topic = CODING_TOPICS[day % len(CODING_TOPICS)]
            scheduled_date = start_date + timedelta(days=day)

            task = Task.objects.create(
                session_key=session_key,
                plan=plan,
                title=f"Study {topic}",
                topic=topic,
                scheduled_date=scheduled_date,
                estimated_minutes=daily_minutes,
            )

            tasks.append({
                "id": task.id,
                "title": task.title,
                "topic": task.topic,
                "scheduled_date": task.scheduled_date.isoformat(),
                "estimated_minutes": task.estimated_minutes,
                "completed": task.completed,
            })

    return {
        "id": plan.id,
        "goal": plan.goal,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "daily_minutes": plan.daily_minutes,
        "tasks": tasks,
    }
