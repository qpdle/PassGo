from django.contrib import admin
from django.urls import include, path
from accounts.api import CsrfView, SignupView, LoginView, LogoutView, MeView
from .views import health, demo_events

urlpatterns = [
    path("api/v1/auth/csrf/", CsrfView.as_view()),
    path("api/v1/auth/signup/", SignupView.as_view()),
    path("api/v1/auth/login/", LoginView.as_view()),
    path("api/v1/auth/logout/", LogoutView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/", include("events.urls")),
    path("api/v1/demo/events/", demo_events),
    path("admin/", admin.site.urls),
    path("api/v1/health", health),
    path("api/v1/health/", health),
]
