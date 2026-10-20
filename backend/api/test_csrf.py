
from django.test import Client, TestCase, override_settings


@override_settings(MOCK_AI=True)
class CsrfProtectionTests(TestCase):

    def setUp(self):
        # Unlike the default Django test client,
        # this client enforces CSRF checks.
        self.client = Client(enforce_csrf_checks=True)

    def test_chat_without_token_is_rejected(self):
        response = self.client.post(
            "/api/chat/",
            data='{"message":"Show my tasks"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_generate_without_token_is_rejected(self):
        response = self.client.post(
            "/api/plans/generate/",
            data='{"goal":"Coding interview","days":3,"daily_minutes":60}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_reschedule_without_token_is_rejected(self):
        response = self.client.post(
            "/api/plans/1/reschedule/",
        )
        self.assertEqual(response.status_code, 403)

    def test_valid_token_allows_plan_creation(self):
        response = self.client.get("/api/csrf/")
        self.assertEqual(response.status_code, 200)

        token = response.json()["csrfToken"]

        response = self.client.post(
            "/api/plans/generate/",
            data='{"goal":"Coding interview","days":3,"daily_minutes":60}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["tasks"]), 3)
