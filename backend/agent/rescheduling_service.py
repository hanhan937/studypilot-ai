
from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from api.models import StudyPlan, Task


def reschedule_study_plan(plan_id: int) -> dict:
    """
    Move overdue unfinished tasks to available future dates.
    Never change completed tasks or exceed the daily time budget.
    """

    if isinstance(plan_id, bool) or not isinstance(plan_id, int) or plan_id <= 0:
        raise ValueError("Plan ID must be a positive integer.")

    today = timezone.localdate()

    with transaction.atomic():
        plan = StudyPlan.objects.select_for_update().get(id=plan_id)

        overdue_tasks = list(
            Task.objects.filter(
                plan=plan,
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

        # Remove overdue tasks from their old dates before recalculating.
        overdue_ids = [task.id for task in overdue_tasks]

        scheduled_tasks = Task.objects.filter(
            plan=plan,
            scheduled_date__gte=today,
        ).exclude(id__in=overdue_ids)

        # Include completed tasks when calculating daily capacity.
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
            while used_minutes.get(target_date, 0) + minutes > plan.daily_minutes:
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
