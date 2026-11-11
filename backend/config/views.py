from django.db import DatabaseError, connection
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response(
            {"status": "unavailable"}, status=503, headers={"Cache-Control": "no-store"}
        )
    return Response({"status": "ok"}, headers={"Cache-Control": "no-store"})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def demo_events(request):
    from django.conf import settings

    if not settings.DEBUG:
        return Response(status=404)
    return Response(
        {
            "results": [
                {
                    "id": "demo-1",
                    "title": "Встреча IT сообщества",
                    "description": "Тестовый ответ сервера для проверки интерфейса. Это не опубликованное мероприятие.",
                    "capacity": 100,
                }
            ]
        },
        headers={"Cache-Control": "no-store"},
    )
