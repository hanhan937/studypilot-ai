
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from api.models import StudyPlan, Task
from agent.task_service import validate_session_key


def reschedule_study_plan(
    plan_id: int,
    *,
    session_key: str,
) -> dict:
    """
    Reschedule overdue unfinished tasks for one guest session.

    Completed tasks are not moved.
    Daily study time limits are preserved.
    Extend the plan if necessary.
    """

    session_key = validate_session_key(session_key)

    if (
        isinstance(plan_id, bool)
        or not isinstance(plan_id, int)
        or plan_id <= 0
    ):
        raise ValueError("Plan ID must be a positive integer.")

    today = timezone.localdate()

    with transaction.atomic():
        # A visitor can only access their own plan.
        # A missing or foreign plan produces the same result.
        plan = StudyPlan.objects.select_for_update().get(
            id=plan_id,
            session_key=session_key,
        )

        overdue_tasks = list(
            Task.objects.filter(
                plan=plan,
                session_key=session_key,
                completed=False,
                scheduled_date__lt=today,
            ).order_by("scheduled_date", "id")
        )

        if not overdue_tasks:
            return {
                "plan_id": plan.id,
                "rescheduled_count": 0,
                "new_end_date": plan.end_date.isoformat(),
                "rescheduled_tasks": [],
            }

        overdue_ids = [task.id for task in overdue_tasks]

        # Calculate occupied time within this visitor's plan.
        scheduled_tasks = Task.objects.filter(
            plan=plan,
            session_key=session_key,
            scheduled_date__gte=today,
        ).exclude(id__in=overdue_ids)

        used_minutes = {}

        for task in scheduled_tasks:
            date = task.scheduled_date
            used_minutes[date] = (
                used_minutes.get(date, 0)
                + (task.estimated_minutes or 0)
            )

        changes = []
        latest_date = plan.end_date

        for task in overdue_tasks:
            minutes = task.estimated_minutes or 0

            if minutes > plan.daily_minutes:
                raise ValueError(
                    f"Task {task.id} exceeds the daily time limit."
                )

            target_date = today

            while (
                used_minutes.get(target_date, 0) + minutes
                > plan.daily_minutes
            ):
                target_date += timedelta(days=1)

            old_date = task.scheduled_date

            task.scheduled_date = target_date
            task.save(update_fields=["scheduled_date"])

            used_minutes[target_date] = (
                used_minutes.get(target_date, 0) + minutes
            )

            latest_date = max(latest_date, target_date)

            changes.append({
                "task_id": task.id,
                "title": task.title,
                "old_date": old_date.isoformat(),
                "new_date": target_date.isoformat(),
            })

        if latest_date > plan.end_date:
            plan.end_date = latest_date
            plan.save(update_fields=["end_date"])

        return {
            "plan_id": plan.id,
            "rescheduled_count": len(changes),
            "new_end_date": plan.end_date.isoformat(),
            "rescheduled_tasks": changes,
        }
