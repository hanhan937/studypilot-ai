
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

from api.models import Task


def create_task(
    title: str,
    topic: str = "",
    scheduled_date: str | None = None,
    estimated_minutes: int | None = None,
) -> dict:
    """Create and save a study task."""
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


def list_tasks() -> list[dict]:
    """Retrieve saved study tasks."""
    return list(
        Task.objects.order_by("-created_at", "-id").values(
            "id",
            "title",
            "topic",
            "scheduled_date",
            "estimated_minutes",
            "completed",
        )
    )


def complete_task(task_id: int) -> dict:
    """Mark a task as completed."""
    try:
        task = Task.objects.get(id=task_id)
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


def get_progress() -> dict:
    """Calculate overall task completion progress."""
    total = Task.objects.count()
    completed = Task.objects.filter(completed=True).count()

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
