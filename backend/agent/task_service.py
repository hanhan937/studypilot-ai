
from django.utils.dateparse import parse_date

from api.models import Task


def validate_session_key(session_key: str) -> str:
    """Require a valid Django session key."""
    if (
        not isinstance(session_key, str)
        or not session_key
        or len(session_key) > 40
    ):
        raise ValueError("A valid session key is required.")

    return session_key


def create_task(
    title: str,
    topic: str = "",
    scheduled_date: str | None = None,
    estimated_minutes: int | None = None,
    *,
    session_key: str,
) -> dict:
    """Create a task belonging to one guest session."""
    session_key = validate_session_key(session_key)

    if not isinstance(title, str):
        raise ValueError("Task title must be a string.")

    title = title.strip()

    if not title:
        raise ValueError("Task title cannot be empty.")

    if len(title) > 200:
        raise ValueError("Task title is too long.")

    date_value = None
    if scheduled_date:
        date_value = parse_date(scheduled_date)
        if date_value is None:
            raise ValueError("Invalid date. Use YYYY-MM-DD.")

    if estimated_minutes is not None and estimated_minutes <= 0:
        raise ValueError("Estimated minutes must be positive.")

    task = Task(
        session_key=session_key,
        title=title,
        topic=topic,
        scheduled_date=date_value,
        estimated_minutes=estimated_minutes,
    )

    task.full_clean()
    task.save()

    return {
        "id": task.id,
        "title": task.title,
        "topic": task.topic,
        "completed": task.completed,
    }


def list_tasks(*, session_key: str) -> list[dict]:
    """Retrieve tasks for one guest session only."""
    session_key = validate_session_key(session_key)

    return list(
        Task.objects.filter(
            session_key=session_key
        ).order_by("-created_at", "-id").values(
            "id",
            "title",
            "topic",
            "scheduled_date",
            "estimated_minutes",
            "completed",
        )
    )


def complete_task(task_id: int, *, session_key: str) -> dict:
    """Complete a task belonging to the current session."""
    session_key = validate_session_key(session_key)

    try:
        task = Task.objects.get(
            id=task_id,
            session_key=session_key,
        )
    except Task.DoesNotExist:
        raise ValueError("Task not found.")

    if not task.completed:
        task.completed = True
        task.save(update_fields=["completed"])

    return {
        "id": task.id,
        "title": task.title,
        "completed": task.completed,
    }


def get_progress(*, session_key: str) -> dict:
    """Calculate progress for one guest session only."""
    session_key = validate_session_key(session_key)

    tasks = Task.objects.filter(session_key=session_key)

    total = tasks.count()
    completed = tasks.filter(completed=True).count()

    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
        "completion_percentage": (
            round(completed / total * 100, 1)
            if total > 0
            else 0
        ),
    }
