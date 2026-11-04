"""Mọi lỗi API trả cùng định dạng `ErrorDTO` (04 mục 3, mục 5.1).

`exception_handler` lo lỗi trong view DRF; `shared.api.views` lo route lạ, lỗi ngoài DRF và
exception không bắt qua `handler400`/`403`/`404`/`500` của Django. Hai nơi dùng chung
`error_body`.
"""

from typing import Any

import structlog
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from shared.exceptions import DomainError

VALIDATION_ERROR_MESSAGE = _("Dữ liệu gửi lên không hợp lệ.")


def current_request_id() -> str:
    """`request_id` mà `django-structlog` gắn vào contextvars cho request hiện tại."""
    return str(structlog.contextvars.get_contextvars().get("request_id", ""))


def error_body(
    code: str, message: str | Promise, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": str(message),
            "details": details or {},
            "request_id": current_request_id(),
        }
    }


def _join(prefix: str, key: object) -> str:
    return f"{prefix}.{key}" if prefix else str(key)


def _flatten_fields(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    """Làm phẳng `ValidationError.detail` thành `{field_path: [str]}`, path nối bằng dấu chấm."""
    # Ví dụ {"lines": [{}, {"sku": ["..."]}]} thành {"lines.1.sku": ["..."]}
    if isinstance(detail, dict):
        children = [(_join(prefix, key), value) for key, value in detail.items()]
    elif isinstance(detail, list) and any(isinstance(item, dict | list) for item in detail):
        # Lỗi của list serializer (`many=True`): mỗi phần tử một index, bỏ qua phần tử hợp lệ
        children = [(_join(prefix, index), item) for index, item in enumerate(detail) if item]
    else:
        messages = detail if isinstance(detail, list) else [detail]
        return {prefix or api_settings.NON_FIELD_ERRORS_KEY: [str(m) for m in messages]}

    fields: dict[str, list[str]] = {}
    for path, value in children:
        fields.update(_flatten_fields(value, path))
    return fields


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """`EXCEPTION_HANDLER` của DRF. Trả `None` cho exception lạ để Django gọi `handler500`."""
    if isinstance(exc, DomainError):
        set_rollback()
        return Response(error_body(exc.code, exc.message, exc.details), status=exc.http_status)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    # Handler mặc định giữ header (`WWW-Authenticate`, `Retry-After`) và rollback transaction
    response = drf_exception_handler(exc, context)
    if response is None or not isinstance(exc, exceptions.APIException):
        return response

    if isinstance(exc, exceptions.ValidationError):
        response.data = error_body(
            "VALIDATION_ERROR",
            VALIDATION_ERROR_MESSAGE,
            {"fields": _flatten_fields(exc.detail)},
        )
    else:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.default_detail)
        response.data = error_body(str(exc.default_code).upper(), message)
    return response
