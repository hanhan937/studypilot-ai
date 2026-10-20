
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from api.models import StudyPlan, Task
from agent.rescheduling_service import reschedule_study_plan


class ReschedulingServiceTests(TestCase):

    def setUp(self):
        self.today = timezone.localdate()
        self.session_key = "test_guest_session_A"
        self.other_session_key = "test_guest_session_B"

        self.plan = StudyPlan.objects.create(
            session_key=self.session_key,
            goal="Coding interview preparation",
            start_date=self.today - timedelta(days=2),
            end_date=self.today + timedelta(days=1),
            daily_minutes=120,
        )

    def create_task(
        self,
        title,
        day_offset,
        minutes=120,
        completed=False,
    ):
        return Task.objects.create(
            session_key=self.session_key,
            plan=self.plan,
            title=title,
            scheduled_date=self.today + timedelta(days=day_offset),
            estimated_minutes=minutes,
            completed=completed,
        )

    def test_reschedules_overdue_task(self):
        overdue = self.create_task("Arrays", -1)

        result = reschedule_study_plan(
            self.plan.id,
            session_key=self.session_key,
        )

        overdue.refresh_from_db()

        self.assertEqual(result["rescheduled_count"], 1)
        self.assertEqual(overdue.scheduled_date, self.today)

    def test_does_not_move_completed_task(self):
        completed = self.create_task(
            "Completed task",
            -1,
            completed=True,
        )

        result = reschedule_study_plan(
            self.plan.id,
            session_key=self.session_key,
        )

        completed.refresh_from_db()

        self.assertEqual(result["rescheduled_count"], 0)
        self.assertEqual(
            completed.scheduled_date,
            self.today - timedelta(days=1),
        )

    def test_respects_daily_time_limit(self):
        self.create_task("Existing task", 0, 90)
        overdue = self.create_task("Overdue task", -1, 60)

        reschedule_study_plan(
            self.plan.id,
            session_key=self.session_key,
        )

        overdue.refresh_from_db()

        self.assertEqual(
            overdue.scheduled_date,
            self.today + timedelta(days=1),
        )

    def test_extends_plan_when_days_are_full(self):
        self.plan.end_date = self.today + timedelta(days=1)
        self.plan.save(update_fields=["end_date"])

        self.create_task("Today", 0)
        self.create_task("Tomorrow", 1)
        overdue = self.create_task("Overdue", -1)

        result = reschedule_study_plan(
            self.plan.id,
            session_key=self.session_key,
        )

        overdue.refresh_from_db()
        self.plan.refresh_from_db()

        expected_date = self.today + timedelta(days=2)

        self.assertEqual(overdue.scheduled_date, expected_date)
        self.assertEqual(self.plan.end_date, expected_date)
        self.assertEqual(
            result["new_end_date"],
            expected_date.isoformat(),
        )

    def test_rejects_invalid_plan_id(self):
        for invalid_id in [0, -1, True, "abc"]:
            with self.subTest(plan_id=invalid_id):
                with self.assertRaises(ValueError):
                    reschedule_study_plan(
                        invalid_id,
                        session_key=self.session_key,
                    )

    def test_cannot_reschedule_another_guests_plan(self):
        """
        Visitor B must not be able to change Visitor A's plan,
        even if B knows the plan ID.
        """
        overdue = self.create_task("Private Arrays", -1)
        original_date = overdue.scheduled_date
        original_end_date = self.plan.end_date

        with self.assertRaises(StudyPlan.DoesNotExist):
            reschedule_study_plan(
                self.plan.id,
                session_key=self.other_session_key,
            )

        overdue.refresh_from_db()
        self.plan.refresh_from_db()

        self.assertEqual(
            overdue.scheduled_date,
            original_date,
        )
        self.assertEqual(
            self.plan.end_date,
            original_end_date,
        )
        self.assertFalse(overdue.completed)
