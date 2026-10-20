
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import StudyPlan, Task


class GuestIsolationTests(TestCase):

    def setUp(self):
        self.visitor_a = APIClient()
        self.visitor_b = APIClient()

    def create_plan(self, client, goal):
        return client.post(
            "/api/plans/generate/",
            {
                "goal": goal,
                "days": 3,
                "daily_minutes": 60,
            },
            format="json",
        )

    def test_visitors_cannot_see_each_others_plans(self):
        response = self.create_plan(
            self.visitor_a,
            "Visitor A coding interview",
        )
        self.assertEqual(response.status_code, 201)

        response = self.create_plan(
            self.visitor_b,
            "Visitor B Python interview",
        )
        self.assertEqual(response.status_code, 201)

        plans_a = self.visitor_a.get("/api/plans/").json()["plans"]
        plans_b = self.visitor_b.get("/api/plans/").json()["plans"]

        self.assertEqual(len(plans_a), 1)
        self.assertEqual(len(plans_b), 1)
        self.assertEqual(plans_a[0]["goal"], "Visitor A coding interview")
        self.assertEqual(plans_b[0]["goal"], "Visitor B Python interview")

    def test_visitors_cannot_see_each_others_tasks(self):
        self.create_plan(self.visitor_a, "Visitor A study plan")
        self.create_plan(self.visitor_b, "Visitor B study plan")

        tasks_a = self.visitor_a.get("/api/tasks/").json()["tasks"]
        tasks_b = self.visitor_b.get("/api/tasks/").json()["tasks"]

        self.assertEqual(len(tasks_a), 3)
        self.assertEqual(len(tasks_b), 3)

        ids_a = {task["id"] for task in tasks_a}
        ids_b = {task["id"] for task in tasks_b}

        self.assertTrue(ids_a.isdisjoint(ids_b))

    def test_visitor_cannot_reschedule_another_plan(self):
        response = self.create_plan(
            self.visitor_a,
            "Visitor A private plan",
        )
        plan_id = response.json()["id"]

        response = self.visitor_b.post(
            f"/api/plans/{plan_id}/reschedule/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_old_unowned_records_are_not_visible(self):
        Task.objects.create(
            title="Legacy private task",
            session_key=None,
        )

        response = self.visitor_a.get("/api/tasks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tasks"], [])
        
    
    def test_chat_cannot_complete_another_visitors_task(self):
        from django.test import override_settings

        with override_settings(MOCK_AI=True):
            response = self.visitor_a.post(
                "/api/chat/",
                {"message": "Create a task called Private Algorithms"},
                format="json",
            )
            self.assertEqual(response.status_code, 200)

            task = Task.objects.get(title="Private Algorithms")

            response = self.visitor_b.post(
                "/api/chat/",
                {"message": f"Mark task {task.id} as completed"},
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(
                "could not find",
                response.json()["reply"].lower(),
            )

            task.refresh_from_db()
            self.assertFalse(task.completed)

    def test_chat_progress_is_separate_for_each_visitor(self):
        from django.test import override_settings

        with override_settings(MOCK_AI=True):
            self.visitor_a.post(
                "/api/chat/",
                {"message": "Create a task called Arrays"},
                format="json",
            )

            response_a = self.visitor_a.post(
                "/api/chat/",
                {"message": "What's my study progress?"},
                format="json",
            )

            response_b = self.visitor_b.post(
                "/api/chat/",
                {"message": "What's my study progress?"},
                format="json",
            )

            self.assertEqual(response_a.status_code, 200)
            self.assertEqual(response_b.status_code, 200)

            self.assertIn("0 of 1", response_a.json()["reply"])
            self.assertIn("0 of 0", response_b.json()["reply"])

