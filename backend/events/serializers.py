from datetime import datetime

from rest_framework import serializers

from accounts.api import user_data
from config.api import StrictSerializer


class IdInput(serializers.RegexField):
    def __init__(self):
        super().__init__(r"^[1-9][0-9]{0,18}$")

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Передайте идентификатор строкой.")
        return super().to_internal_value(data)


class DateInput(serializers.DateTimeField):
    def to_internal_value(self, data):
        try:
            parsed = datetime.fromisoformat(data.replace("Z", "+00:00"))
            if parsed.utcoffset() is None:
                raise serializers.ValidationError("Укажите время с часовым поясом.")
        except (AttributeError, TypeError, ValueError):
            raise serializers.ValidationError("Укажите дату и время с часовым поясом.")
        return super().to_internal_value(data)


class VenueInput(StrictSerializer):
    name = serializers.CharField(max_length=200)
    address = serializers.CharField(max_length=5000)


class RoomInput(StrictSerializer):
    name = serializers.CharField(max_length=100)
    capacity = serializers.IntegerField(min_value=1, max_value=2147483647)


class EventInput(StrictSerializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, max_length=30000)
    timezone = serializers.CharField(max_length=64)
    starts_at = DateInput()
    ends_at = DateInput()
    registration_opens_at = DateInput()
    registration_closes_at = DateInput()
    capacity = serializers.IntegerField(min_value=1, max_value=2147483647)


class EventRoomInput(StrictSerializer):
    room_id = IdInput()


class ProgramInput(StrictSerializer):
    event_room_id = IdInput()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, max_length=30000)
    speaker = serializers.CharField(allow_blank=True, max_length=200)
    starts_at = DateInput()
    ends_at = DateInput()


class StaffInput(StrictSerializer):
    email = serializers.EmailField(max_length=254)


def iso(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def venue_data(obj):
    return {
        "id": str(obj.pk),
        "owner_id": str(obj.owner_id),
        "name": obj.name,
        "address": obj.address,
        "created_at": iso(obj.created_at),
    }


def room_data(obj):
    return {
        "id": str(obj.pk),
        "venue_id": str(obj.venue_id),
        "name": obj.name,
        "capacity": obj.capacity,
    }


def event_data(obj):
    from django.utils import timezone

    status = obj.status
    if status == "published" and obj.ends_at <= timezone.now():
        status = "completed"
    result = {"id": str(obj.pk), "owner_id": str(obj.owner_id), "status": status}
    for field in ("title", "description", "timezone", "capacity"):
        result[field] = getattr(obj, field)
    for field in (
        "starts_at",
        "ends_at",
        "registration_opens_at",
        "registration_closes_at",
        "checkin_opens_at",
        "created_at",
        "updated_at",
        "published_at",
        "cancelled_at",
    ):
        result[field] = iso(getattr(obj, field))
    return result


def event_room_data(obj):
    draft = obj.event.published_at is None
    return {
        "id": str(obj.pk),
        "event_id": str(obj.event_id),
        "room_id": str(obj.room_id),
        "name_snapshot": obj.room.name if draft else obj.name_snapshot,
        "address_snapshot": obj.room.venue.address if draft else obj.address_snapshot,
        "capacity_snapshot": obj.room.capacity if draft else obj.capacity_snapshot,
    }


def program_data(obj):
    return {
        "id": str(obj.pk),
        "event_room_id": str(obj.event_room_id),
        "title": obj.title,
        "description": obj.description,
        "speaker": obj.speaker,
        "starts_at": iso(obj.starts_at),
        "ends_at": iso(obj.ends_at),
    }


def staff_data(obj):
    return {
        "id": str(obj.pk),
        "event_id": str(obj.event_id),
        "user": user_data(obj.user),
        "created_at": iso(obj.created_at),
    }
