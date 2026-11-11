from django.contrib import admin
from .models import Event, Room, Venue


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Event)
class EventAdmin(ReadOnlyAdmin):
    list_display = ("title", "status", "owner", "starts_at", "capacity")
    list_filter = ("status",)
    search_fields = ("title",)


@admin.register(Venue)
class VenueAdmin(ReadOnlyAdmin):
    list_display = ("name", "address", "owner")
    search_fields = ("name", "address")


@admin.register(Room)
class RoomAdmin(ReadOnlyAdmin):
    list_display = ("name", "venue", "capacity")
