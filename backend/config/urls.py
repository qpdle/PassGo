from django.contrib import admin
from django.urls import path
from .views import health, demo_events

urlpatterns = [
    path("api/v1/demo/events/", demo_events),
    path("admin/", admin.site.urls),
    path("api/v1/health", health),
    path("api/v1/health/", health),
]
