from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Venue(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="venues")
    name = models.CharField("название", max_length=200)
    address = models.TextField("адрес")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "площадка"
        verbose_name_plural = "площадки"

    def __str__(self):
        return self.name


class Room(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="rooms")
    name = models.CharField("название", max_length=100)
    capacity = models.PositiveIntegerField("вместимость")

    class Meta:
        verbose_name = "помещение"
        verbose_name_plural = "помещения"
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="room_capacity_positive"),
            models.UniqueConstraint(fields=["venue", "name"], name="room_venue_name_unique"),
        ]

    def __str__(self):
        return f"{self.venue}: {self.name}"


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"
        CANCELLED = "cancelled", "Отменено"
        COMPLETED = "completed", "Завершено"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="events")
    title = models.CharField("название", max_length=200)
    description = models.TextField("описание", blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    timezone = models.CharField("часовой пояс", max_length=64, default="Europe/Moscow")
    starts_at = models.DateTimeField("начало")
    ends_at = models.DateTimeField("окончание")
    registration_opens_at = models.DateTimeField("открытие регистрации")
    registration_closes_at = models.DateTimeField("закрытие регистрации")
    checkin_opens_at = models.DateTimeField("открытие входа")
    capacity = models.PositiveIntegerField("лимит участников")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "мероприятие"
        verbose_name_plural = "мероприятия"
        indexes = [models.Index(fields=["status", "starts_at"], name="event_status_start_idx"), models.Index(fields=["owner", "created_at"], name="event_owner_created_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["draft", "published", "cancelled", "completed"]), name="event_valid_status"),
            models.CheckConstraint(condition=Q(capacity__gt=0), name="event_capacity_positive"),
            models.CheckConstraint(condition=Q(starts_at__lt=F("ends_at")), name="event_dates_ordered"),
            models.CheckConstraint(condition=Q(registration_opens_at__lt=F("registration_closes_at")) & Q(registration_closes_at__lte=F("starts_at")), name="event_registration_window"),
            models.CheckConstraint(condition=Q(checkin_opens_at__lt=F("ends_at")), name="event_checkin_window"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            errors["timezone"] = "Укажите действительный часовой пояс IANA."
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            errors["ends_at"] = "Окончание должно быть позже начала."
        if self.registration_opens_at and self.registration_closes_at and self.registration_opens_at >= self.registration_closes_at:
            errors["registration_closes_at"] = "Закрытие регистрации должно быть позже открытия."
        if self.registration_closes_at and self.starts_at and self.registration_closes_at > self.starts_at:
            errors["registration_closes_at"] = "Регистрация закрывается не позднее начала мероприятия."
        if self.checkin_opens_at and self.starts_at and self.checkin_opens_at != self.starts_at - timedelta(minutes=60):
            errors["checkin_opens_at"] = "Вход открывается за 60 минут до начала."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title
