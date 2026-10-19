from django.test import SimpleTestCase


class HealthEndpointTests(SimpleTestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "message": "StudyPilot API is running"},
        )
