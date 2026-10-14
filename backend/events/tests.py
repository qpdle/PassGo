from datetime import datetime, timedelta, timezone
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from .models import Event, Room, Venue


class ModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("owner@example.com", full_name="Организатор")
        self.venue = Venue.objects.create(owner=self.owner, name="Зал", address="Вымышленный адрес")

    def event(self, **changes):
        starts = datetime(2026, 11, 7, 7, tzinfo=timezone.utc)
        values = {"owner": self.owner, "title": "Демо", "starts_at": starts, "ends_at": starts + timedelta(hours=2), "registration_opens_at": starts - timedelta(days=1), "registration_closes_at": starts, "checkin_opens_at": starts - timedelta(minutes=60), "capacity": 100}
        values.update(changes)
        return Event(**values)

    def test_event_validation_and_timezone(self):
        self.event().full_clean()
        with self.assertRaises(ValidationError):
            self.event(timezone="Unknown/City").full_clean()
        with self.assertRaises(ValidationError):
            self.event(checkin_opens_at=datetime(2026, 11, 7, 7, tzinfo=timezone.utc)).full_clean()

    def test_database_blocks_invalid_event(self):
        for changes in [{"capacity": 0}, {"status": "unknown"}, {"ends_at": datetime(2026, 11, 7, 6, tzinfo=timezone.utc)}, {"registration_closes_at": datetime(2026, 11, 7, 8, tzinfo=timezone.utc)}, {"checkin_opens_at": datetime(2026, 11, 8, 8, tzinfo=timezone.utc)}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.event(**changes).save()

    def test_room_capacity_and_unique_name(self):
        Room.objects.create(venue=self.venue, name="Главный", capacity=100)
        for values in [{"name": "Другой", "capacity": 0}, {"name": "Главный", "capacity": 50}]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Room.objects.create(venue=self.venue, **values)

    def test_owner_and_venue_deletion_protected(self):
        Room.objects.create(venue=self.venue, name="Главный", capacity=100)
        with self.assertRaises(ProtectedError):
            self.owner.delete()
        with self.assertRaises(ProtectedError):
            self.venue.delete()

    @override_settings(DEBUG=True)
    def test_demo_seed_repeatable_without_privileges_or_passwords(self):
        call_command("seed_demo", stdout=StringIO())
        users = get_user_model().objects.filter(email__endswith="@passgo.example")
        before = list(users.values_list("pk", "password"))
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(before, list(users.values_list("pk", "password")))
        self.assertEqual(users.count(), 3)
        self.assertTrue(all(not u.is_staff and not u.is_superuser and not u.has_usable_password() for u in users))
        self.assertEqual(Event.objects.filter(title="Демо встреча IT сообщества").count(), 1)
        self.assertEqual(Room.objects.filter(venue__name="Демо учебный центр").count(), 2)

    @override_settings(DEBUG=False)
    def test_demo_seed_disabled_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_demo_seed_does_not_overwrite_existing_account(self):
        get_user_model().objects.create_user("organizer@passgo.example", "Existing-password-592!", full_name="Другой пользователь")
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertFalse(get_user_model().objects.filter(email="participant@passgo.example").exists())

    def test_business_admin_models_read_only(self):
        admin = get_user_model().objects.create_superuser("admin@example.com", "Strong-test-pass-592!", full_name="Админ")
        self.client.force_login(admin)
        for model in ["event", "venue", "room"]:
            self.assertEqual(self.client.get(f"/admin/events/{model}/add/").status_code, 403)
