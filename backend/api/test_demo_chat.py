
"""
Tests for StudyPilot AI Chat API.

Demo Mode uses fixed commands without calling OpenAI.
Real Mode uses the agent service.

All task operations must use the current guest session.
"""

import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from agent.exceptions import AgentConfigError
from api.models import Task


@override_settings(MOCK_AI=True)
class DemoModeChatTests(TestCase):
    """Test deterministic Demo Mode commands."""

    def chat(self, message: str) -> str:
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code,
            200,
            response.content,
        )
        self.assertEqual(response.json()["mode"], "demo")

        return response.json()["reply"]

    def test_create_task_persists_in_sqlite(self):
        reply = self.chat("Create a task called Binary Search")

        self.assertIn("Created task", reply)

        task = Task.objects.get(title="Binary Search")

        self.assertFalse(task.completed)
        self.assertEqual(
            task.session_key,
            self.client.session.session_key,
        )

    def test_show_tasks_empty_then_with_tasks(self):
        reply = self.chat("Show my tasks")
        self.assertIn("no tasks yet", reply.lower())

        self.chat("Create a task called Binary Search")

        reply = self.chat("Show my tasks")
        self.assertIn("Binary Search", reply)

    def test_mark_completed_by_title_persists_in_sqlite(self):
        self.chat("Create a task called Binary Search")

        reply = self.chat(
            "Mark Binary Search as completed"
        )

        self.assertIn("Marked task", reply)

        task = Task.objects.get(title="Binary Search")
        self.assertTrue(task.completed)

    def test_can_complete_by_id_after_clarification(self):
        self.chat("Create a task called Graph Basics")
        self.chat("Create a task called Graph Traversal")

        reply = self.chat("Mark Graph as completed")

        self.assertIn("More than one task", reply)
        self.assertEqual(
            Task.objects.filter(completed=True).count(),
            0,
        )

        task = Task.objects.get(title="Graph Basics")

        reply = self.chat(
            f"Mark task {task.id} as completed"
        )

        self.assertIn("Marked task", reply)

        task.refresh_from_db()
        self.assertTrue(task.completed)

    def test_completing_twice_does_not_claim_new_success(self):
        self.chat("Create a task called Binary Search")

        self.chat("Mark Binary Search as completed")

        reply = self.chat(
            "Mark Binary Search as completed"
        )

        self.assertIn("already completed", reply.lower())

    def test_created_task_appears_in_tasks_endpoint(self):
        self.chat("Create a task called Binary Search")

        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, 200)

        tasks = response.json()["tasks"]

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Binary Search")

    def test_demo_mode_never_calls_the_openai_agent(self):
        with patch(
            "api.chat_view.run_study_agent",
            side_effect=AssertionError(
                "Real agent must not run in Demo Mode"
            ),
        ) as agent:
            reply = self.chat(
                "Create a task called Binary Search"
            )

        self.assertIn("Demo Mode", reply)
        agent.assert_not_called()

    def test_empty_message_is_rejected(self):
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_multiple_matches_ask_for_clarification_and_change_nothing(self):
        self.chat("Create a task called Graph Basics")
        self.chat("Create a task called Graph Traversal")

        reply = self.chat("Mark Graph as completed")

        self.assertIn("More than one task", reply)

        self.assertEqual(
            Task.objects.filter(completed=True).count(),
            0,
        )

    def test_progress_reflects_database(self):
        self.chat("Create a task called Binary Search")
        self.chat("Create a task called Sliding Window")

        self.chat("Mark Binary Search as completed")

        reply = self.chat("What's my study progress?")

        self.assertIn("1 of 2", reply)
        self.assertIn("50.0%", reply)

    def test_unknown_task_is_not_reported_as_success(self):
        reply = self.chat(
            "Mark Quantum Physics as completed"
        )

        self.assertIn("could not find", reply.lower())

        self.assertEqual(Task.objects.count(), 0)

    def test_unsupported_command_gets_honest_fallback_and_changes_nothing(self):
        reply = self.chat(
            "Plan my whole semester and reschedule my exams"
        )

        self.assertIn("don't recognize", reply.lower())
        self.assertEqual(Task.objects.count(), 0)


@override_settings(MOCK_AI=False)
class RealModeStillWorksTests(TestCase):
    """Test the Real Mode API without making real OpenAI calls."""

    def post(self, message: str):
        return self.client.post(
            "/api/chat/",
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    def test_health_endpoint_still_works(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_real_mode_errors_are_not_hidden_by_demo_replies(self):
        with patch(
            "api.chat_view.run_study_agent",
            side_effect=AgentConfigError(
                "API key is not configured"
            ),
        ):
            response = self.post("Hello")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["mode"], "real")
        self.assertIn("error", response.json())

    def test_real_mode_uses_the_agent_and_reports_mode_real(self):
        with (
            patch(
                "api.chat_view.run_study_agent",
                return_value="Hi from the agent",
            ) as agent,
            patch(
                "api.chat_view.handle_demo_command",
                side_effect=AssertionError(
                    "Demo handler must not run in Real Mode"
                ),
            ),
        ):
            response = self.post(
                "Create a task called Binary Search"
            )

            self.assertEqual(
                response.status_code,
                200,
                response.content,
            )

            self.assertEqual(
                response.json(),
                {
                    "reply": "Hi from the agent",
                    "mode": "real",
                },
            )

            agent.assert_called_once()

            args, kwargs = agent.call_args

            self.assertEqual(
                args,
                ("Create a task called Binary Search",),
            )

            self.assertEqual(
                kwargs["session_key"],
                self.client.session.session_key,
            )

            # The mocked real agent must not create a task.
            self.assertEqual(Task.objects.count(), 0)
