from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class SessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def post(self, path, data):
        token = self.client.get("/api/v1/auth/csrf/").json()["csrf_token"]
        return self.client.post(
            "/api/v1/auth/" + path + "/", data, format="json", HTTP_X_CSRFTOKEN=token
        )

    def signup(self):
        return self.post(
            "signup",
            {
                "email": " Person@Example.test ",
                "full_name": "Тестовый пользователь",
                "password": "Different_StrongPass39!",
            },
        )

    def test_signup_session_and_logout(self):
        response = self.signup()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.json()["email"], "person@example.test")
        self.assertNotIn("password", response.json())
        self.assertTrue(User.objects.get().check_password("Different_StrongPass39!"))
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
        self.assertTrue(self.client.cookies["sessionid"]["httponly"])
        self.assertEqual(self.post("logout", {}).status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_login_normalizes_email_and_rejects_bad_password(self):
        self.signup()
        self.post("logout", {})
        self.assertEqual(
            self.post(
                "login", {"email": "PERSON@example.test", "password": "wrong"}
            ).json()["code"],
            "invalid_credentials",
        )
        self.assertEqual(
            self.post(
                "login",
                {"email": "PERSON@example.test", "password": "Different_StrongPass39!"},
            ).status_code,
            200,
        )

    def test_anonymous_auth_requests_require_csrf(self):
        for name in ["signup", "login"]:
            response = self.client.post(f"/api/v1/auth/{name}/", {}, format="json")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["code"], "csrf_failed")

    def test_session_mutations_require_csrf(self):
        self.signup()
        response = self.client.post("/api/v1/events/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "csrf_failed")

    def test_duplicate_and_weak_password(self):
        self.signup()
        self.assertEqual(self.signup().status_code, 400)
        response = self.post(
            "signup",
            {
                "email": "second@example.test",
                "full_name": "Второй",
                "password": "12345678",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["field_errors"])

    def test_login_rate_limited(self):
        for _ in range(10):
            self.assertEqual(
                self.post(
                    "login", {"email": "missing@example.test", "password": "wrong"}
                ).status_code,
                401,
            )
        response = self.post(
            "login", {"email": "missing@example.test", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_inactive_user_cannot_login(self):
        self.signup()
        self.post("logout", {})
        User.objects.update(is_active=False)
        self.assertEqual(
            self.post(
                "login",
                {"email": "person@example.test", "password": "Different_StrongPass39!"},
            ).status_code,
            401,
        )
