import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EventRoom",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name_snapshot", models.CharField(max_length=100)),
                ("address_snapshot", models.TextField()),
                ("capacity_snapshot", models.PositiveIntegerField()),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="event_rooms",
                        to="events.event",
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="events.room",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EventStaff",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_assignments",
                        to="events.event",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="event_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProgramItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("speaker", models.CharField(blank=True, max_length=200)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="program",
                        to="events.event",
                    ),
                ),
                (
                    "event_room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="program",
                        to="events.eventroom",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="eventroom",
            constraint=models.UniqueConstraint(
                fields=("event", "room"), name="event_room_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="eventroom",
            constraint=models.CheckConstraint(
                condition=models.Q(("capacity_snapshot__gt", 0)),
                name="event_room_capacity_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="eventstaff",
            constraint=models.UniqueConstraint(
                fields=("event", "user"), name="event_staff_unique"
            ),
        ),
        migrations.AddIndex(
            model_name="programitem",
            index=models.Index(
                fields=["event_room", "starts_at", "ends_at"],
                name="program_room_time_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="programitem",
            constraint=models.CheckConstraint(
                condition=models.Q(("starts_at__lt", models.F("ends_at"))),
                name="program_dates_ordered",
            ),
        ),
    ]
