from unittest.mock import patch

from django.db import OperationalError
from unittest import TestCase
from rest_framework.test import APIClient


class HealthTests(TestCase):
    def test_database_unavailable_returns_503_without_details(self):
        with patch(
            "config.views.connection.cursor",
            side_effect=OperationalError("private connection details"),
        ):
            response = APIClient().get("/api/v1/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_health_only_accepts_get(self):
        self.assertEqual(APIClient().post("/api/v1/health/").status_code, 405)

    def test_demo_available_only_in_debug(self):
        from django.test import override_settings

        with override_settings(DEBUG=True):
            response = APIClient().get("/api/v1/demo/events/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["results"]), 1)
        with override_settings(DEBUG=False):
            self.assertEqual(APIClient().get("/api/v1/demo/events/").status_code, 404)
