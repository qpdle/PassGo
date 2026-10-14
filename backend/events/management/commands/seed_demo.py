from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from events.models import Event, Room, Venue


class Command(BaseCommand):
    help = "Создать повторяемые вымышленные данные без паролей и административного доступа."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Демонстрационные данные разрешены только при DEBUG=true.")
        User = get_user_model()
        people = [("organizer@passgo.example", "Демо организатор"), ("participant@passgo.example", "Демо участник"), ("staff@passgo.example", "Демо сотрудник")]
        users = []
        for email, name in people:
            user, created = User.objects.get_or_create(email=email, defaults={"full_name": name})
            if not created and (user.full_name != name or user.is_staff or user.is_superuser or user.has_usable_password()):
                raise CommandError(f"Существующий аккаунт {email} отличается от демонстрационного. Данные не изменены.")
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            users.append(user)
        venue, _ = Venue.objects.get_or_create(owner=users[0], name="Демо учебный центр", defaults={"address": "Вымышленный адрес 1"})
        Room.objects.get_or_create(venue=venue, name="Главный зал", defaults={"capacity": 100})
        Room.objects.get_or_create(venue=venue, name="Малый зал", defaults={"capacity": 40})
        starts = datetime(2026, 11, 7, 7, tzinfo=timezone.utc)
        event, created = Event.objects.get_or_create(owner=users[0], title="Демо встреча IT сообщества", defaults={"description": "Вымышленные данные для проверки каркаса", "starts_at": starts, "ends_at": starts + timedelta(hours=8), "registration_opens_at": starts - timedelta(days=14), "registration_closes_at": starts, "checkin_opens_at": starts - timedelta(minutes=60), "capacity": 100})
        event.full_clean()
        self.stdout.write(self.style.SUCCESS(f"Демо набор готов: 3 пользователя, площадка, 2 помещения и черновик. event_id={event.pk}; created={created}."))
