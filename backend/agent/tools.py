
import json

from agents import RunContextWrapper, function_tool

from . import task_service
from .context import StudyAgentContext


@function_tool
def create_task(
    ctx: RunContextWrapper[StudyAgentContext],
    title: str,
    topic: str = "",
    scheduled_date: str | None = None,
    estimated_minutes: int | None = None,
) -> str:
    """Create a study task for the current visitor."""
    try:
        result = task_service.create_task(
            title=title,
            topic=topic,
            scheduled_date=scheduled_date,
            estimated_minutes=estimated_minutes,
            session_key=ctx.context.session_key,
        )
        return json.dumps(result, default=str)
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": str(exc)})


@function_tool
def list_tasks(
    ctx: RunContextWrapper[StudyAgentContext],
) -> str:
    """List study tasks belonging to the current visitor."""
    result = task_service.list_tasks(
        session_key=ctx.context.session_key,
    )
    return json.dumps(result, default=str)


@function_tool
def complete_task(
    ctx: RunContextWrapper[StudyAgentContext],
    task_id: int,
) -> str:
    """Complete one of the current visitor's tasks."""
    try:
        result = task_service.complete_task(
            task_id,
            session_key=ctx.context.session_key,
        )
        return json.dumps(result)
    except (ValueError, TypeError) as exc:
        return json.dumps({"error": str(exc)})


@function_tool
def get_progress(
    ctx: RunContextWrapper[StudyAgentContext],
) -> str:
    """Get study progress for the current visitor."""
    result = task_service.get_progress(
        session_key=ctx.context.session_key,
    )
    return json.dumps(result)
