import hashlib
import hmac
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import ApiError, StrictSerializer
from .models import AuthRateLimit, User, normalize_email


def user_data(user):
    return {"id": str(user.pk), "email": user.email, "full_name": user.full_name}


class LoginInput(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        trim_whitespace=False, max_length=128, write_only=True
    )


class SignupInput(LoginInput):
    full_name = serializers.CharField(max_length=150)

    def validate(self, data):
        try:
            validate_password(
                data["password"], User(email=data["email"], full_name=data["full_name"])
            )
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages})
        return data


def rate_limit(request, action):
    # На стенде Caddy перезаписывает X-Real-IP; порт Django снаружи закрыт.
    behind_proxy = os.environ.get("DJANGO_BEHIND_PROXY", "false").lower() == "true"
    address = request.META.get("HTTP_X_REAL_IP") if behind_proxy else None
    address = address or request.META.get("REMOTE_ADDR", "unknown")
    digest = hmac.new(
        settings.SECRET_KEY.encode(), f"{action}:{address}".encode(), hashlib.sha256
    ).hexdigest()
    now = timezone.now()
    window, maximum = (60, 10) if action == "login" else (3600, 20)
    with transaction.atomic():
        AuthRateLimit.objects.get_or_create(key=digest, defaults={"started_at": now})
        row = AuthRateLimit.objects.select_for_update().get(pk=digest)
        if row.started_at + timedelta(seconds=window) <= now:
            row.started_at, row.attempts = now, 0
        if row.attempts >= maximum:
            raise Throttled(
                wait=max(
                    1,
                    int(
                        (
                            row.started_at + timedelta(seconds=window) - now
                        ).total_seconds()
                    ),
                )
            )
        row.attempts += 1
        row.save(update_fields=["attempts", "started_at"])
    AuthRateLimit.objects.filter(started_at__lt=now - timedelta(days=1)).delete()


@method_decorator(csrf_protect, name="dispatch")
class AuthView(APIView):
    permission_classes = [AllowAny]


class CsrfView(AuthView):
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class SignupView(AuthView):
    def post(self, request):
        rate_limit(request, "signup")
        serializer = SignupInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = normalize_email(data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": ["Этот email уже используется."]})
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email, password=data["password"], full_name=data["full_name"]
                )
        except (IntegrityError, DjangoValidationError):
            raise ValidationError({"email": ["Этот email уже используется."]})
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(user_data(user), status=201)


class LoginView(AuthView):
    def post(self, request):
        rate_limit(request, "login")
        serializer = LoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = authenticate(
            request, email=normalize_email(data["email"]), password=data["password"]
        )
        if user is None:
            raise ApiError("invalid_credentials", "Неверный email или пароль.", 401)
        login(request, user)
        return Response(user_data(user))


class LogoutView(APIView):
    def post(self, request):
        serializer = StrictSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout(request)
        return Response(status=204)


class MeView(APIView):
    def get(self, request):
        return Response(user_data(request.user))
