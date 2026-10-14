from django.urls import path
from .views import health

urlpatterns = [path("api/v1/health", health), path("api/v1/health/", health)]
