from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from .models import Event, EventRoom, EventStaff, ProgramItem, Room, Venue


def event_input():
    start = timezone.now().replace(microsecond=0) + timedelta(days=10)
    return {
        "title": "Тестовая конференция",
        "description": "Доклады и встречи",
        "timezone": "Europe/Moscow",
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=5)).isoformat(),
        "registration_opens_at": (start - timedelta(days=5)).isoformat(),
        "registration_closes_at": start.isoformat(),
        "capacity": 100,
    }


def fixtures():
    owner = User.objects.create_user(
        "owner@example.test", "Strong_test_pass37", full_name="Организатор"
    )
    other = User.objects.create_user(
        "other@example.test", "Strong_test_pass38", full_name="Другой пользователь"
    )
    venue = Venue.objects.create(
        owner=owner, name="Учебный центр", address="Тестовый адрес"
    )
    rooms = [
        Room.objects.create(venue=venue, name=f"Зал {i}", capacity=60)
        for i in range(1, 3)
    ]
    client = APIClient()
    client.force_authenticate(owner)
    event = client.post("/api/v1/events/", event_input(), format="json").json()
    return owner, other, venue, rooms, client, event


class EventApiTests(TestCase):
    def setUp(self):
        self.owner, self.other, self.venue, self.rooms, self.client, self.event = (
            fixtures()
        )
        self.path = f"/api/v1/events/{self.event['id']}/"

    def assign(self, room=None):
        response = self.client.post(
            self.path + "rooms/",
            {"room_id": str((room or self.rooms[0]).pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.json()

    def program(self, room_id, start=None, end=None):
        event = Event.objects.get(pk=self.event["id"])
        return {
            "title": "Доклад",
            "description": "",
            "speaker": "Спикер",
            "event_room_id": room_id,
            "starts_at": (start or event.starts_at).isoformat(),
            "ends_at": (end or event.starts_at + timedelta(hours=1)).isoformat(),
        }

    def publish(self):
        for room in self.rooms:
            self.assign(room)
        response = self.client.post(self.path + "publish/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_full_flow_and_guest_program(self):
        assigned = [self.assign(r) for r in self.rooms]
        response = self.client.post(
            self.path + "program/", self.program(assigned[0]["id"]), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 200
        )
        guest = APIClient()
        self.assertEqual(guest.get(self.path).json()["status"], "published")
        self.assertEqual(guest.get(self.path + "program/").json()["count"], 1)
        self.assertEqual(guest.get(self.path + "rooms/").json()["count"], 2)
        self.assertEqual(guest.get("/api/v1/events/").json()["count"], 1)

    def test_private_draft_and_owner_checks(self):
        self.assertEqual(APIClient().get(self.path).status_code, 404)
        self.client.force_authenticate(self.other)
        for suffix in ["", "rooms/", "program/", "staff/"]:
            self.assertEqual(self.client.get(self.path + suffix).status_code, 404)
        for method, suffix, data in [
            ("patch", "", {"title": "Чужое"}),
            ("post", "publish/", {}),
            ("post", "cancel/", {}),
            ("post", "rooms/", {"room_id": str(self.rooms[0].pk)}),
            ("post", "staff/", {"email": self.owner.email}),
        ]:
            response = getattr(self.client, method)(
                self.path + suffix, data, format="json"
            )
            self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(self.client.get("/api/v1/me/events/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/v1/venues/").json()["count"], 0)

    def test_anonymous_cannot_write(self):
        response = APIClient().post("/api/v1/events/", event_input(), format="json")
        self.assertEqual(response.status_code, 401)
        self.assertIn("WWW-Authenticate", response)

    def test_validation_and_unknown_fields(self):
        for data in [
            {"timezone": "No/Such_Zone"},
            {"capacity": 0},
            {"owner_id": "99"},
            {"ends_at": self.event["starts_at"]},
            {"registration_closes_at": self.event["ends_at"]},
        ]:
            self.assertEqual(
                self.client.patch(self.path, data, format="json").status_code, 400
            )
        self.assertEqual(
            self.client.get("/api/v1/events/?page_size=101").status_code, 400
        )

    def test_venue_and_room_operations(self):
        response = self.client.post(
            "/api/v1/venues/", {"name": "Новая", "address": "Адрес"}, format="json"
        )
        venue_path = f"/api/v1/venues/{response.json()['id']}/"
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            venue_path + "rooms/", {"name": "Комната", "capacity": 20}, format="json"
        )
        room_path = venue_path + f"rooms/{response.json()['id']}/"
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.post(
                venue_path + "rooms/",
                {"name": "Комната", "capacity": 10},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(self.client.delete(venue_path).status_code, 409)
        self.assertEqual(
            self.client.patch(room_path, {"capacity": 30}, format="json").json()[
                "capacity"
            ],
            30,
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.patch(room_path, {"capacity": 1}, format="json").status_code,
            404,
        )
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(room_path).status_code, 204)
        self.assertEqual(self.client.delete(venue_path).status_code, 204)

    def test_assignment_duplicates_and_protected_room(self):
        self.assign()
        response = self.client.post(
            self.path + "rooms/", {"room_id": str(self.rooms[0].pk)}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "room_already_assigned")
        self.assertEqual(
            self.client.delete(
                f"/api/v1/venues/{self.venue.pk}/rooms/{self.rooms[0].pk}/"
            ).status_code,
            409,
        )

    def test_cannot_assign_other_owner_room(self):
        venue = Venue.objects.create(owner=self.other, name="Чужая", address="Адрес")
        room = Room.objects.create(venue=venue, name="Чужой зал", capacity=100)
        self.assertEqual(
            self.client.post(
                self.path + "rooms/", {"room_id": str(room.pk)}, format="json"
            ).status_code,
            404,
        )

    def test_program_intervals_and_room_ownership(self):
        first, second = self.assign(self.rooms[0]), self.assign(self.rooms[1])
        data = self.program(first["id"])
        self.assertEqual(
            self.client.post(self.path + "program/", data, format="json").status_code,
            201,
        )
        self.assertEqual(
            self.client.post(self.path + "program/", data, format="json").json()[
                "code"
            ],
            "program_overlap",
        )
        data["event_room_id"] = second["id"]
        self.assertEqual(
            self.client.post(self.path + "program/", data, format="json").status_code,
            201,
        )
        obj = Event.objects.get(pk=self.event["id"])
        adjacent = self.program(
            first["id"],
            obj.starts_at + timedelta(hours=1),
            obj.starts_at + timedelta(hours=2),
        )
        self.assertEqual(
            self.client.post(
                self.path + "program/", adjacent, format="json"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.delete(self.path + f"rooms/{first['id']}/").status_code, 409
        )
        outside = self.program(
            first["id"], obj.starts_at - timedelta(hours=1), obj.starts_at
        )
        self.assertEqual(
            self.client.post(
                self.path + "program/", outside, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                self.path,
                {"starts_at": (obj.starts_at + timedelta(minutes=10)).isoformat()},
                format="json",
            ).status_code,
            400,
        )

    def test_program_patch_delete_and_after_start_lock(self):
        assigned = self.assign()
        response = self.client.post(
            self.path + "program/", self.program(assigned["id"]), format="json"
        )
        path = self.path + f"program/{response.json()['id']}/"
        self.assertEqual(
            self.client.patch(path, {"title": "Изменено"}, format="json").json()[
                "title"
            ],
            "Изменено",
        )
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assign(self.rooms[1])
        self.client.post(self.path + "publish/", {}, format="json")
        with patch(
            "events.api.timezone.now",
            return_value=Event.objects.get(pk=self.event["id"]).starts_at,
        ):
            self.assertEqual(
                self.client.post(
                    self.path + "program/", self.program(assigned["id"]), format="json"
                ).status_code,
                409,
            )

    def test_publish_capacity_snapshots_and_fixed_fields(self):
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 400
        )
        self.assign()
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 400
        )
        self.assign(self.rooms[1])
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 200
        )
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 200
        )
        self.client.patch(
            f"/api/v1/venues/{self.venue.pk}/rooms/{self.rooms[0].pk}/",
            {"capacity": 1, "name": "Другое"},
            format="json",
        )
        assigned = self.client.get(self.path + "rooms/").json()["results"]
        self.assertEqual(assigned[0]["capacity_snapshot"], 60)
        self.assertEqual(assigned[0]["name_snapshot"], "Зал 1")
        self.assertEqual(
            self.client.patch(
                self.path, {"timezone": "UTC"}, format="json"
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.patch(self.path, {"capacity": 121}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                self.path + "rooms/", {"room_id": str(self.rooms[0].pk)}, format="json"
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.patch(
                self.path, {"description": "Новое описание"}, format="json"
            ).status_code,
            200,
        )

    def test_staff_scope_and_remove(self):
        path = self.path + "staff/"
        self.assertEqual(
            self.client.post(
                path, {"email": "missing@example.test"}, format="json"
            ).json()["code"],
            "user_not_found",
        )
        response = self.client.post(
            path, {"email": self.other.email.upper()}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.post(
                path, {"email": self.other.email}, format="json"
            ).status_code,
            409,
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.patch(
                self.path, {"title": "Сотрудник"}, format="json"
            ).status_code,
            404,
        )
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.delete(path + response.json()["id"] + "/").status_code, 204
        )
        self.assertFalse(EventStaff.objects.exists())

    def test_cancel_and_completed_status(self):
        self.publish()
        response = self.client.post(self.path + "cancel/", {}, format="json")
        self.assertEqual(response.json()["status"], "cancelled")
        self.assertEqual(
            self.client.post(self.path + "cancel/", {}, format="json").status_code, 200
        )
        self.assertEqual(
            self.client.post(self.path + "publish/", {}, format="json").status_code, 409
        )
        self.assertEqual(
            self.client.patch(self.path, {"title": "Нет"}, format="json").status_code,
            409,
        )

    def test_errors_have_request_id_and_private_cache(self):
        response = self.client.get("/api/v1/no-such-route/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["request_id"], response["X-Request-ID"])
        self.assertEqual(response["Cache-Control"], "no-store")
        response = self.client.put(self.path, {}, format="json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()["code"], "method_not_allowed")

    def test_pagination_and_empty_patch_follow_contract(self):
        self.assertEqual(
            self.client.patch(self.path, {}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.get("/api/v1/me/events/?unknown=1").status_code, 400
        )
        self.client.post("/api/v1/events/", event_input(), format="json")
        response = self.client.get("/api/v1/me/events/?page_size=1").json()
        self.assertEqual(len(response["results"]), 1)
        self.assertTrue(response["next"].startswith("/api/v1/me/events/?"))

    def test_dates_require_offset_and_ids_require_strings(self):
        response = self.client.patch(
            self.path, {"starts_at": "2026-12-01T10:00:00"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            self.path + "rooms/", {"room_id": self.rooms[0].pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_program_cannot_use_assignment_from_other_event(self):
        other = self.client.post("/api/v1/events/", event_input(), format="json").json()
        path = f"/api/v1/events/{other['id']}/rooms/"
        assignment = self.client.post(
            path, {"room_id": str(self.rooms[0].pk)}, format="json"
        ).json()
        response = self.client.post(
            self.path + "program/", self.program(assignment["id"]), format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_completion_uses_server_time(self):
        self.publish()
        ended = Event.objects.get(pk=self.event["id"]).ends_at
        with patch("django.utils.timezone.now", return_value=ended):
            self.assertEqual(self.client.get(self.path).json()["status"], "completed")
        with patch("events.api.timezone.now", return_value=ended):
            self.assertEqual(
                self.client.post(self.path + "cancel/", {}, format="json").status_code,
                409,
            )


class ConcurrentProgramTests(TransactionTestCase):
    def test_two_requests_cannot_create_overlapping_program(self):
        owner, _, _, rooms, client, event = fixtures()
        path = f"/api/v1/events/{event['id']}/"
        assignment = client.post(
            path + "rooms/", {"room_id": str(rooms[0].pk)}, format="json"
        ).json()
        data = {
            "event_room_id": assignment["id"],
            "title": "Параллельная запись",
            "description": "",
            "speaker": "",
            "starts_at": event["starts_at"],
            "ends_at": (
                Event.objects.get(pk=event["id"]).starts_at + timedelta(hours=1)
            ).isoformat(),
        }
        barrier = Barrier(2)

        def create(_):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(User.objects.get(pk=owner.pk))
                barrier.wait(timeout=10)
                return api.post(path + "program/", data, format="json").status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(create, range(2)))
        self.assertEqual(sorted(statuses), [201, 409])
        self.assertEqual(ProgramItem.objects.count(), 1)
