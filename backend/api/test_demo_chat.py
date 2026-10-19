"""
Tests for Demo Mode chat commands (MOCK_AI=true) and the explicit "mode" field.

- Tasks are created / completed through the REAL agent/task_service.py functions and are checked
  directly in the SQLite test database (not just in the HTTP response).
- Every Demo Mode test runs with a network guard: any socket connection, HTTP request, or call
  into the OpenAI agent makes the test fail.
"""
from unittest.mock import patch

from django.apps import apps
from django.test import TestCase, override_settings

from agent.exceptions import AgentConfigError


def task_model():
    """Find the Task model without hard-coding the app name."""
    return next(model for model in apps.get_models() if model.__name__ == "Task")


def _blocked(*args, **kwargs):
    raise AssertionError("Demo Mode must never make a network or OpenAI request.")


@override_settings(MOCK_AI=True, OPENAI_API_KEY="")
class DemoModeChatTests(TestCase):
    def setUp(self):
        guards = [
            patch("socket.socket.connect", new=_blocked),
            patch("httpx.Client.send", new=_blocked),
            patch("httpx.AsyncClient.send", new=_blocked),
        ]
        for guard in guards:
            guard.start()
            self.addCleanup(guard.stop)

        # The OpenAI agent entry point must never be called in Demo Mode.
        agent_patch = patch(
            "api.chat_view.run_study_agent", side_effect=AssertionError("OpenAI agent was called")
        )
        self.agent_mock = agent_patch.start()
        self.addCleanup(agent_patch.stop)

    def chat(self, message):
        response = self.client.post(
            "/api/chat/", data={"message": message}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["mode"], "demo")  # explicit mode indicator
        return body["reply"]

    # ----- create -----
    def test_create_task_persists_in_sqlite(self):
        reply = self.chat("Create a task called Binary Search")
        self.assertIn("Created task", reply)
        self.assertIn("[Demo Mode]", reply)

        Task = task_model()
        task = Task.objects.get(title="Binary Search")
        self.assertFalse(task.completed)
        self.assertEqual(Task.objects.count(), 1)

    def test_created_task_appears_in_tasks_endpoint(self):
        self.chat("Create a task called Binary Search")
        titles = [task["title"] for task in self.client.get("/api/tasks/").json()["tasks"]]
        self.assertIn("Binary Search", titles)

    # ----- list -----
    def test_show_tasks_empty_then_with_tasks(self):
        self.assertIn("no tasks yet", self.chat("Show my tasks"))
        self.chat("Create a task called Binary Search")
        self.assertIn("Binary Search", self.chat("Show my tasks"))

    # ----- complete -----
    def test_mark_completed_by_title_persists_in_sqlite(self):
        self.chat("Create a task called Binary Search")
        reply = self.chat("Mark Binary Search as completed")
        self.assertIn("Marked task", reply)
        self.assertTrue(task_model().objects.get(title="Binary Search").completed)

    def test_multiple_matches_ask_for_clarification_and_change_nothing(self):
        self.chat("Create a task called Graph Basics")
        self.chat("Create a task called Graph Traversal")
        reply = self.chat("Mark Graph as completed")
        self.assertIn("More than one task matches", reply)
        self.assertNotIn("Marked task", reply)
        self.assertEqual(task_model().objects.filter(completed=True).count(), 0)

    def test_can_complete_by_id_after_clarification(self):
        self.chat("Create a task called Graph Basics")
        self.chat("Create a task called Graph Traversal")
        second = task_model().objects.get(title="Graph Traversal")
        self.chat(f"Mark task {second.pk} as completed")
        self.assertEqual(
            list(task_model().objects.filter(completed=True).values_list("title", flat=True)),
            ["Graph Traversal"],
        )

    def test_unknown_task_is_not_reported_as_success(self):
        reply = self.chat("Mark Quantum Physics as completed")
        self.assertIn("could not find", reply)
        self.assertNotIn("Marked task", reply)

    def test_completing_twice_does_not_claim_new_success(self):
        self.chat("Create a task called Binary Search")
        self.chat("Mark Binary Search as completed")
        reply = self.chat("Mark Binary Search as completed")
        self.assertIn("already completed", reply)
        self.assertNotIn("Marked task", reply)

    # ----- progress -----
    def test_progress_reflects_database(self):
        self.chat("Create a task called Binary Search")
        self.chat("Create a task called Two Pointers")
        self.chat("Mark Binary Search as completed")
        reply = self.chat("What's my study progress?")
        self.assertIn("1 of 2", reply)
        self.assertIn("50.0%", reply)

    # ----- fallback -----
    def test_unsupported_command_gets_honest_fallback_and_changes_nothing(self):
        reply = self.chat("Plan my whole semester and reschedule my exams")
        self.assertIn("don't recognize", reply)
        self.assertIn("fixed commands", reply)
        self.assertIn("not AI reasoning", reply)
        self.assertEqual(task_model().objects.count(), 0)

    # ----- no OpenAI -----
    def test_demo_mode_never_calls_the_openai_agent(self):
        for message in (
            "Create a task called A",
            "Show my tasks",
            "Mark A as completed",
            "What's my study progress?",
            "something unsupported",
        ):
            self.chat(message)  # the guards in setUp fail the test on any OpenAI/network use
        self.agent_mock.assert_not_called()

    # ----- validation -----
    def test_empty_message_is_rejected(self):
        response = self.client.post(
            "/api/chat/", data={"message": "   "}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())


@override_settings(MOCK_AI=False)
class RealModeStillWorksTests(TestCase):
    def post(self, message="hello"):
        return self.client.post(
            "/api/chat/", data={"message": message}, content_type="application/json"
        )

    def test_real_mode_uses_the_agent_and_reports_mode_real(self):
        with patch("api.chat_view.run_study_agent", return_value="Hi from the agent") as agent, patch(
            "api.chat_view.handle_demo_command", side_effect=AssertionError("demo handler used")
        ):
            response = self.post("Create a task called Binary Search")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "Hi from the agent", "mode": "real"})
        agent.assert_called_once_with("Create a task called Binary Search")
        self.assertEqual(task_model().objects.count(), 0)  # demo parser did not run

    @override_settings(OPENAI_API_KEY="")
    def test_real_mode_errors_are_not_hidden_by_demo_replies(self):
        with patch("api.chat_view.run_study_agent", side_effect=AgentConfigError("no key")):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["mode"], "real")

    def test_health_endpoint_still_works(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")