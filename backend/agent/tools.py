
import json

from agents import function_tool

from . import task_service


@function_tool
def create_task(
    title: str,
    topic: str = "",
    scheduled_date: str | None = None,
    estimated_minutes: int | None = None,
) -> str:
    """Create a study task and save it in the database."""
    try:
        result = task_service.create_task(
            title=title,
            topic=topic,
            scheduled_date=scheduled_date,
            estimated_minutes=estimated_minutes,
        )
        return json.dumps(result, default=str)
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": str(exc)})


@function_tool
def list_tasks() -> str:
    """List all saved study tasks and their status."""
    result = task_service.list_tasks()
    return json.dumps(result, default=str)


@function_tool
def complete_task(task_id: int) -> str:
    """Mark a study task as completed using its task ID."""
    try:
        result = task_service.complete_task(task_id)
        return json.dumps(result)
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": str(exc)})


@function_tool
def get_progress() -> str:
    """Get total, completed, remaining tasks and completion percentage."""
    result = task_service.get_progress()
    return json.dumps(result)
