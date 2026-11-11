from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from config.api import ApiError, StrictSerializer, page_response
from .models import Event, EventRoom, EventStaff, ProgramItem, Room, Venue
from .serializers import (
    EventInput,
    EventRoomInput,
    ProgramInput,
    RoomInput,
    StaffInput,
    VenueInput,
    event_data,
    event_room_data,
    program_data,
    room_data,
    staff_data,
    venue_data,
)


def validated(schema, request, partial=False):
    serializer = schema(data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    if partial and not serializer.validated_data:
        raise ValidationError(
            {"non_field_errors": ["Укажите хотя бы одно изменяемое поле."]}
        )
    return serializer.validated_data


def signed_in(request):
    if not request.user.is_authenticated:
        raise NotAuthenticated()


def owned_event(request, event_id):
    signed_in(request)
    return get_object_or_404(
        Event.objects.select_for_update(), pk=event_id, owner=request.user
    )


def visible_event(request, event_id):
    query = Q(status__in=["published", "completed"]) | Q(
        status="cancelled", published_at__isnull=False
    )
    if request.user.is_authenticated:
        query |= Q(owner=request.user)
    return get_object_or_404(Event.objects.filter(query), pk=event_id)


def editable(event, draft_only=False):
    if event.status == "draft":
        return
    if (
        not draft_only
        and event.status == "published"
        and timezone.now() < event.starts_at
    ):
        return
    raise ApiError("invalid_transition", "В этом состоянии изменение недоступно.")


def model_validation(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(
            exc.message_dict
            if hasattr(exc, "message_dict")
            else {"non_field_errors": exc.messages}
        )


class VenueList(APIView):
    def get(self, request):
        return page_response(
            request, Venue.objects.filter(owner=request.user).order_by("pk"), venue_data
        )

    def post(self, request):
        obj = Venue.objects.create(owner=request.user, **validated(VenueInput, request))
        return Response(venue_data(obj), status=201)


class VenueDetail(APIView):
    def get(self, request, venue_id):
        return Response(
            venue_data(get_object_or_404(Venue, pk=venue_id, owner=request.user))
        )

    @transaction.atomic
    def patch(self, request, venue_id):
        obj = get_object_or_404(
            Venue.objects.select_for_update(), pk=venue_id, owner=request.user
        )
        for key, value in validated(VenueInput, request, partial=True).items():
            setattr(obj, key, value)
        obj.save()
        return Response(venue_data(obj))

    @transaction.atomic
    def delete(self, request, venue_id):
        obj = get_object_or_404(
            Venue.objects.select_for_update(), pk=venue_id, owner=request.user
        )
        if obj.rooms.exists():
            raise ApiError("venue_in_use", "Сначала удалите помещения площадки.")
        obj.delete()
        return Response(status=204)


class RoomList(APIView):
    def get(self, request, venue_id):
        venue = get_object_or_404(Venue, pk=venue_id, owner=request.user)
        return page_response(request, venue.rooms.order_by("pk"), room_data)

    @transaction.atomic
    def post(self, request, venue_id):
        venue = get_object_or_404(
            Venue.objects.select_for_update(), pk=venue_id, owner=request.user
        )
        data = validated(RoomInput, request)
        if venue.rooms.filter(name=data["name"]).exists():
            raise ValidationError(
                {"name": ["В этой площадке уже есть помещение с таким названием."]}
            )
        return Response(room_data(Room.objects.create(venue=venue, **data)), status=201)


class RoomDetail(APIView):
    @transaction.atomic
    def patch(self, request, venue_id, room_id):
        get_object_or_404(
            Venue.objects.select_for_update(), pk=venue_id, owner=request.user
        )
        obj = get_object_or_404(
            Room.objects.select_for_update(), pk=room_id, venue_id=venue_id
        )
        data = validated(RoomInput, request, partial=True)
        if (
            "name" in data
            and Room.objects.filter(venue_id=venue_id, name=data["name"])
            .exclude(pk=obj.pk)
            .exists()
        ):
            raise ValidationError(
                {"name": ["В этой площадке уже есть помещение с таким названием."]}
            )
        for key, value in data.items():
            setattr(obj, key, value)
        obj.save()
        return Response(room_data(obj))

    @transaction.atomic
    def delete(self, request, venue_id, room_id):
        get_object_or_404(
            Venue.objects.select_for_update(), pk=venue_id, owner=request.user
        )
        obj = get_object_or_404(
            Room.objects.select_for_update(), pk=room_id, venue_id=venue_id
        )
        if obj.assignments.exists():
            raise ApiError("room_in_use", "Помещение используется в мероприятии.")
        try:
            obj.delete()
        except ProtectedError:
            raise ApiError("room_in_use", "Помещение используется в мероприятии.")
        return Response(status=204)


class EventList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        events = Event.objects.filter(status__in=["published", "completed"]).order_by(
            "starts_at", "pk"
        )
        return page_response(request, events, event_data)

    def post(self, request):
        signed_in(request)
        data = validated(EventInput, request)
        obj = Event(
            owner=request.user,
            checkin_opens_at=data["starts_at"] - timedelta(minutes=60),
            **data,
        )
        model_validation(obj)
        obj.save()
        return Response(event_data(obj), status=201)


class MyEvents(APIView):
    def get(self, request):
        return page_response(
            request,
            Event.objects.filter(owner=request.user).order_by("-created_at", "-pk"),
            event_data,
        )


class EventDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        return Response(event_data(visible_event(request, event_id)))

    @transaction.atomic
    def patch(self, request, event_id):
        obj = owned_event(request, event_id)
        editable(obj)
        data = validated(EventInput, request, partial=True)
        if obj.status != "draft" and set(data) - {"title", "description", "capacity"}:
            raise ApiError(
                "invalid_transition", "После публикации даты и помещения менять нельзя."
            )
        for key, value in data.items():
            setattr(obj, key, value)
        obj.checkin_opens_at = obj.starts_at - timedelta(minutes=60)
        model_validation(obj)
        if obj.program.filter(
            Q(starts_at__lt=obj.starts_at) | Q(ends_at__gt=obj.ends_at)
        ).exists():
            raise ValidationError(
                {
                    "starts_at": [
                        "Программа должна помещаться в новые границы мероприятия."
                    ]
                }
            )
        if obj.status != "draft":
            total = sum(obj.event_rooms.values_list("capacity_snapshot", flat=True))
            if obj.capacity > total:
                raise ValidationError(
                    {"capacity": ["Лимит превышает вместимость помещений."]}
                )
        obj.save()
        return Response(event_data(obj))


class EventPublish(APIView):
    @transaction.atomic
    def post(self, request, event_id):
        event = owned_event(request, event_id)
        validated(StrictSerializer, request)
        if event.status == "published":
            return Response(event_data(event))
        editable(event, draft_only=True)
        model_validation(event)
        if event.starts_at <= timezone.now():
            raise ValidationError(
                {"starts_at": ["Начало мероприятия должно быть в будущем."]}
            )
        assignments = list(event.event_rooms.order_by("room_id"))
        room_ids = [a.room_id for a in assignments]
        venue_ids = Room.objects.filter(pk__in=room_ids).values_list(
            "venue_id", flat=True
        )
        # Во всех операциях сначала блокируем площадки, затем помещения.
        list(Venue.objects.select_for_update().filter(pk__in=venue_ids).order_by("pk"))
        rooms = {
            r.pk: r
            for r in Room.objects.select_for_update(of=("self",))
            .select_related("venue")
            .filter(pk__in=room_ids)
            .order_by("pk")
        }
        if (
            not assignments
            or sum(rooms[a.room_id].capacity for a in assignments) < event.capacity
        ):
            raise ValidationError(
                {
                    "capacity": [
                        "Назначьте помещения с достаточной суммарной вместимостью."
                    ]
                }
            )
        for item in assignments:
            room = rooms[item.room_id]
            item.name_snapshot, item.address_snapshot, item.capacity_snapshot = (
                room.name,
                room.venue.address,
                room.capacity,
            )
            item.save()
        event.status, event.published_at = "published", timezone.now()
        event.save()
        return Response(event_data(event))


class EventCancel(APIView):
    @transaction.atomic
    def post(self, request, event_id):
        event = owned_event(request, event_id)
        validated(StrictSerializer, request)
        if event.status == "cancelled":
            return Response(event_data(event))
        if event.status == "completed" or (
            event.status == "published" and event.ends_at <= timezone.now()
        ):
            raise ApiError(
                "invalid_transition", "Завершённое мероприятие отменить нельзя."
            )
        event.status, event.cancelled_at = "cancelled", timezone.now()
        event.save()
        return Response(event_data(event))


class EventRooms(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        event = visible_event(request, event_id)
        return page_response(
            request,
            event.event_rooms.select_related("event", "room__venue").order_by("pk"),
            event_room_data,
        )

    @transaction.atomic
    def post(self, request, event_id):
        event = owned_event(request, event_id)
        editable(event, draft_only=True)
        data = validated(EventRoomInput, request)
        candidate = get_object_or_404(
            Room, pk=data["room_id"], venue__owner=request.user
        )
        get_object_or_404(
            Venue.objects.select_for_update(), pk=candidate.venue_id, owner=request.user
        )
        room = get_object_or_404(
            Room.objects.select_for_update(of=("self",)).select_related("venue"),
            pk=data["room_id"],
            venue__owner=request.user,
        )
        if event.event_rooms.filter(room=room).exists():
            raise ApiError("room_already_assigned", "Помещение уже добавлено.")
        obj = EventRoom.objects.create(
            event=event,
            room=room,
            name_snapshot=room.name,
            address_snapshot=room.venue.address,
            capacity_snapshot=room.capacity,
        )
        return Response(event_room_data(obj), status=201)


class EventRoomDetail(APIView):
    @transaction.atomic
    def delete(self, request, event_id, event_room_id):
        event = owned_event(request, event_id)
        editable(event, draft_only=True)
        obj = get_object_or_404(EventRoom, pk=event_room_id, event=event)
        if obj.program.exists():
            raise ApiError(
                "room_in_use", "Сначала удалите выступления в этом помещении."
            )
        obj.delete()
        return Response(status=204)


def write_program(event, request, obj=None):
    editable(event)
    data = validated(ProgramInput, request, partial=obj is not None)
    obj = obj or ProgramItem(event=event)
    for key, value in data.items():
        setattr(obj, key, value)
    get_object_or_404(EventRoom, pk=obj.event_room_id, event=event)
    if not event.starts_at <= obj.starts_at < obj.ends_at <= event.ends_at:
        raise ValidationError(
            {
                "ends_at": [
                    "Время выступления должно быть внутри мероприятия, конец — позже начала."
                ]
            }
        )
    overlap = ProgramItem.objects.filter(
        event_room_id=obj.event_room_id,
        starts_at__lt=obj.ends_at,
        ends_at__gt=obj.starts_at,
    ).exclude(pk=obj.pk)
    if overlap.exists():
        raise ApiError(
            "program_overlap", "В этом помещении на это время уже есть выступление."
        )
    obj.save()
    return obj


class ProgramList(APIView):
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        event = visible_event(request, event_id)
        return page_response(
            request,
            event.program.order_by("starts_at", "pk"),
            program_data,
        )

    @transaction.atomic
    def post(self, request, event_id):
        event = owned_event(request, event_id)
        return Response(program_data(write_program(event, request)), status=201)


class ProgramDetail(APIView):
    @transaction.atomic
    def patch(self, request, event_id, program_item_id):
        event = owned_event(request, event_id)
        obj = get_object_or_404(ProgramItem, pk=program_item_id, event=event)
        return Response(program_data(write_program(event, request, obj)))

    @transaction.atomic
    def delete(self, request, event_id, program_item_id):
        event = owned_event(request, event_id)
        editable(event)
        get_object_or_404(ProgramItem, pk=program_item_id, event=event).delete()
        return Response(status=204)


class StaffList(APIView):
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id, owner=request.user)
        return page_response(
            request,
            event.staff_assignments.select_related("user").order_by("pk"),
            staff_data,
        )

    @transaction.atomic
    def post(self, request, event_id):
        event = owned_event(request, event_id)
        if (
            event.status in ["cancelled", "completed"]
            or event.ends_at <= timezone.now()
        ):
            raise ApiError(
                "invalid_transition",
                "Назначение сотрудников для этого мероприятия закрыто.",
            )
        data = validated(StaffInput, request)
        user = User.objects.filter(email__iexact=data["email"], is_active=True).first()
        if not user:
            raise ApiError(
                "user_not_found", "Пользователь с таким email не найден.", 404
            )
        if event.staff_assignments.filter(user=user).exists():
            raise ApiError("staff_already_assigned", "Сотрудник уже назначен.")
        return Response(
            staff_data(EventStaff.objects.create(event=event, user=user)), status=201
        )


class StaffDetail(APIView):
    @transaction.atomic
    def delete(self, request, event_id, staff_id):
        event = owned_event(request, event_id)
        get_object_or_404(EventStaff, pk=staff_id, event=event).delete()
        return Response(status=204)
