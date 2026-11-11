from django.urls import path
from . import api

urlpatterns = [
    path("events/", api.EventList.as_view()),
    path("me/events/", api.MyEvents.as_view()),
    path("events/<int:event_id>/", api.EventDetail.as_view()),
    path("events/<int:event_id>/publish/", api.EventPublish.as_view()),
    path("events/<int:event_id>/cancel/", api.EventCancel.as_view()),
    path("venues/", api.VenueList.as_view()),
    path("venues/<int:venue_id>/", api.VenueDetail.as_view()),
    path("venues/<int:venue_id>/rooms/", api.RoomList.as_view()),
    path("venues/<int:venue_id>/rooms/<int:room_id>/", api.RoomDetail.as_view()),
    path("events/<int:event_id>/rooms/", api.EventRooms.as_view()),
    path(
        "events/<int:event_id>/rooms/<int:event_room_id>/",
        api.EventRoomDetail.as_view(),
    ),
    path("events/<int:event_id>/program/", api.ProgramList.as_view()),
    path(
        "events/<int:event_id>/program/<int:program_item_id>/",
        api.ProgramDetail.as_view(),
    ),
    path("events/<int:event_id>/staff/", api.StaffList.as_view()),
    path("events/<int:event_id>/staff/<int:staff_id>/", api.StaffDetail.as_view()),
]
