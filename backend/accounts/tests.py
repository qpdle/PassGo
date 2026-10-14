from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .forms import AdminUserCreationForm

User = get_user_model()


class UserTests(TestCase):
    def test_email_normalized_and_password_hashed(self):
        user = User.objects.create_user(" Demo@Example.COM ", "Strong-test-pass-592!", full_name="Демо")
        self.assertEqual(user.email, "demo@example.com")
        self.assertNotEqual(user.password, "Strong-test-pass-592!")
        self.assertTrue(user.check_password("Strong-test-pass-592!"))
        self.assertEqual(authenticate(email="DEMO@EXAMPLE.COM", password="Strong-test-pass-592!"), user)

    def test_database_blocks_case_duplicate_even_for_bulk_create(self):
        User.objects.create_user("demo@example.com", full_name="Демо")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="DEMO@example.com", full_name="Другой")])

    def test_superuser_flags_and_required_password(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", full_name="Админ")
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", "Strong-test-pass-592!", full_name="Админ", is_staff=False)
        admin = User.objects.create_superuser("admin@example.com", "Strong-test-pass-592!", full_name="Админ")
        self.assertTrue(admin.is_staff and admin.is_superuser)

    def test_admin_creation_form_hashes_password(self):
        form = AdminUserCreationForm(data={"email": "form@example.com", "full_name": "Демо", "password1": "Strong-test-pass-592!", "password2": "Strong-test-pass-592!"})
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.check_password("Strong-test-pass-592!"))

    def test_admin_login_and_model_pages(self):
        User.objects.create_superuser("admin@example.com", "Strong-test-pass-592!", full_name="Админ")
        response = self.client.post("/admin/login/", {"username": "ADMIN@example.com", "password": "Strong-test-pass-592!", "next": "/admin/"})
        self.assertEqual(response.status_code, 302)
        for url in ["/admin/", "/admin/accounts/user/", "/admin/events/event/", "/admin/events/venue/", "/admin/events/room/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_non_staff_cannot_enter_admin(self):
        user = User.objects.create_user("ordinary@example.com", full_name="Демо")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
