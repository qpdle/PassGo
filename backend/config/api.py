import uuid
from urllib.parse import urlsplit

from django.http import JsonResponse
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class SessionAuth(SessionAuthentication):
    def authenticate_header(self, request):
        return 'Session realm="PassGo"'

    def enforce_csrf(self, request):
        try:
            super().enforce_csrf(request)
        except PermissionDenied:
            raise ApiError("csrf_failed", "Обновите страницу и повторите запрос.", 403)


class ApiError(APIException):
    def __init__(self, code, message, status=409, fields=None):
        self.status_code = status
        self.api_code = code
        self.fields = fields or {}
        super().__init__(message)


def error_body(request, code, message, fields=None):
    return {
        "code": code,
        "message": message,
        "field_errors": fields or {},
        "request_id": str(getattr(request, "request_id", uuid.uuid4())),
    }


def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_exception_handler

    response = drf_exception_handler(exc, context)
    request = context["request"]
    if isinstance(exc, ApiError):
        body = error_body(request, exc.api_code, str(exc.detail), exc.fields)
    elif isinstance(exc, ValidationError):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = {
                "non_field_errors": detail if isinstance(detail, list) else [detail]
            }
        fields = {
            k: [str(v) for v in (vs if isinstance(vs, list) else [vs])]
            for k, vs in detail.items()
        }
        body = error_body(
            request, "validation_error", "Проверьте заполненные поля.", fields
        )
    else:
        codes = {
            400: ("validation_error", "Некорректный запрос."),
            401: ("not_authenticated", "Войдите в аккаунт."),
            403: ("permission_denied", "Недостаточно прав."),
            404: ("not_found", "Объект не найден."),
            405: ("method_not_allowed", "Этот способ запроса не поддерживается."),
            415: ("unsupported_media_type", "Отправьте данные в формате JSON."),
            429: ("rate_limited", "Слишком много попыток. Попробуйте позже."),
        }
        body = error_body(
            request,
            *codes.get(
                response.status_code if response else 500,
                ("internal_error", "Не удалось выполнить запрос."),
            ),
        )
    if response is None:
        response = Response(status=500)
    response.data = body
    if response.status_code == 401:
        response["WWW-Authenticate"] = 'Session realm="PassGo"'
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        error_body(request, "csrf_failed", "Обновите страницу и повторите запрос."),
        status=403,
    )


class ApiMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            if response.status_code >= 400 and "application/json" not in response.get(
                "Content-Type", ""
            ):
                status = response.status_code
                code, message = (
                    ("not_found", "Объект не найден.")
                    if status == 404
                    else ("internal_error", "Не удалось выполнить запрос.")
                )
                response = JsonResponse(
                    error_body(request, code, message), status=status
                )
            response["X-Request-ID"] = request.request_id
            response["Cache-Control"] = "no-store"
        return response


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise ValidationError(
                    {key: ["Неизвестное поле."] for key in sorted(unknown)}
                )
        return super().to_internal_value(data)


class Page(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    @staticmethod
    def relative(link):
        if link is None:
            return None
        parts = urlsplit(link)
        return parts.path + ("?" + parts.query if parts.query else "")

    def get_next_link(self):
        return self.relative(super().get_next_link())

    def get_previous_link(self):
        return self.relative(super().get_previous_link())


def page_response(request, queryset, render):
    unknown = set(request.query_params) - {"page", "page_size"}
    if unknown:
        raise ValidationError(
            {key: ["Неизвестный параметр."] for key in sorted(unknown)}
        )
    for name, limit in (("page", 2147483647), ("page_size", 100)):
        value = request.query_params.get(name)
        if value is not None and (
            not value.isdecimal() or not 1 <= int(value) <= limit
        ):
            raise ValidationError(
                {name: ["Укажите положительное число в допустимых пределах."]}
            )
    paginator = Page()
    items = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([render(item) for item in items])
