
from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from api.models import StudyPlan, Task
from agent.planning_service import generate_study_plan


class StudyPlanServiceTests(TestCase):

    def test_generate_seven_day_plan(self):
        result = generate_study_plan(
            goal="Prepare for coding interview",
            days=7,
            daily_minutes=120,
        )

        self.assertEqual(StudyPlan.objects.count(), 1)
        self.assertEqual(len(result["tasks"]), 7)
        self.assertEqual(result["daily_minutes"], 120)
        self.assertEqual(
            result["start_date"],
            timezone.localdate().isoformat(),
        )
        self.assertEqual(
            result["end_date"],
            (timezone.localdate() + timedelta(days=6)).isoformat(),
        )

    def test_tasks_linked_to_plan(self):
        result = generate_study_plan("Coding interview", 7, 120)
        plan = StudyPlan.objects.get(id=result["id"])

        self.assertEqual(plan.tasks.count(), 7)
        self.assertTrue(
            all(task.plan_id == plan.id for task in plan.tasks.all())
        )

    def test_daily_time_limit(self):
        generate_study_plan("Coding interview", 14, 90)

        for task in Task.objects.all():
            self.assertLessEqual(task.estimated_minutes, 90)

    def test_invalid_inputs(self):
        invalid_inputs = [
            ("", 7, 120),
            ("Coding interview", 0, 120),
            ("Coding interview", 31, 120),
            ("Coding interview", 7, 10),
            ("Coding interview", 7, 500),
        ]

        for goal, days, minutes in invalid_inputs:
            with self.subTest(goal=goal, days=days, minutes=minutes):
                with self.assertRaises(ValueError):
                    generate_study_plan(goal, days, minutes)

        self.assertEqual(StudyPlan.objects.count(), 0)

    def test_transaction_rollback(self):
        original_create = Task.objects.create
        calls = 0

        def failing_create(*args, **kwargs):
            nonlocal calls
            calls += 1

            if calls == 3:
                raise IntegrityError("Simulated database failure")

            return original_create(*args, **kwargs)

        with patch.object(
            Task.objects,
            "create",
            side_effect=failing_create,
        ):
            with self.assertRaises(IntegrityError):
                generate_study_plan("Coding interview", 7, 120)

        self.assertEqual(StudyPlan.objects.count(), 0)
        self.assertEqual(Task.objects.count(), 0)


        