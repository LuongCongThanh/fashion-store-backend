"""OpenAPI: component `ErrorDTO`, response lỗi mặc định và tag cho mọi operation (04 mục 3, 5.1,
5.6).

`AutoSchema` là `DEFAULT_SCHEMA_CLASS`: thêm 400, 500 cho mọi operation, 429 (kèm header
`Retry-After`) khi view có throttle, 404 khi path có tham số hoặc có query `page` của phân trang,
401/403/503 khi view cần đăng nhập (permission không phải chỉ `AllowAny`); mỗi lỗi mặc định có mô
tả và một ví dụ `ErrorDTO` tiếng Anh. View tự khai mã đặc thù (409, 422…) bằng `extend_schema`; mã
đã khai thì giữ nguyên.

Chữ hiển thị trên Swagger viết tiếng Anh, còn docstring viết tiếng Việt (13 mục 2), nên schema
không lấy docstring của view và serializer: mô tả chỉ đến từ `extend_schema` và
`extend_schema_serializer`. Tag `<store|backoffice> · <module>` suy từ path và package của view.
"""

import re
from typing import Any

from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.plumbing import ComponentRegistry, get_override
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny

from shared.api.pagination import StandardPagination

# Chuỗi thường, không dịch: schema sinh bằng CLI phải giống nhau ở mọi máy (12 mục 5)
ERROR_BODY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Stable error code; the frontend translates by code.",
        },
        "message": {
            "type": "string",
            "description": "Default message in the language of `Accept-Language`.",
        },
        "details": {
            "type": "object",
            "additionalProperties": {},
            "description": (
                "Details by code. `VALIDATION_ERROR`: `{fields: {field_path: string[]}}`; "
                "codes without details: `{}`."
            ),
        },
        "request_id": {"type": "string", "description": "Request ID for looking up logs."},
    },
    "required": ["code", "message", "details", "request_id"],
}

ERROR_DESCRIPTIONS = {
    "400": "Invalid request (`VALIDATION_ERROR`, `PARSE_ERROR`, `BAD_REQUEST`).",
    "401": "Not authenticated or invalid token (`NOT_AUTHENTICATED`, `TOKEN_EXPIRED`).",
    "403": "Insufficient permissions (`PERMISSION_DENIED`).",
    "404": "Not found (`NOT_FOUND`).",
    "429": "Too many requests (`THROTTLED`); retry after `Retry-After` seconds.",
    "500": "Internal error (`INTERNAL_ERROR`).",
    "503": "Authentication state could not be verified in the database (`AUTH_STATE_UNAVAILABLE`).",
}

# Ví dụ chung cho từng lỗi mặc định (mã, message, details); dữ liệu giả
_ERROR_EXAMPLES: dict[str, tuple[str, str, dict[str, Any]]] = {
    "400": (
        "VALIDATION_ERROR",
        "Invalid input.",
        {"fields": {"field_name": ["This field is required."]}},
    ),
    "401": ("NOT_AUTHENTICATED", "Authentication credentials were not provided.", {}),
    "403": ("PERMISSION_DENIED", "You do not have permission to perform this action.", {}),
    "404": ("NOT_FOUND", "Not found.", {}),
    "429": ("THROTTLED", "Request was throttled. Expected available in 30 seconds.", {}),
    "500": ("INTERNAL_ERROR", "Internal server error.", {}),
    "503": ("AUTH_STATE_UNAVAILABLE", "Authentication state is temporarily unavailable.", {}),
}
EXAMPLE_REQUEST_ID = "3f2b8c1e-5d4a-4f6b-9c7e-1a2b3c4d5e6f"

RETRY_AFTER_HEADER: dict[str, Any] = {
    "schema": {"type": "integer"},
    "description": "Seconds to wait before retrying.",
}

# Ứng dụng lấy từ path; path ngoài `/api/v1/store|backoffice/` giữ tag mặc định
API_APP_PATH = re.compile(r"^/api/v1/(?P<app>store|backoffice)/")
# Package chứa module: `modules.identity…` → identity, `shared.geo…` → geo
_MODULE_PACKAGES = ("modules", "shared")


@extend_schema_field(ERROR_BODY_SCHEMA)
class ErrorBodyField(serializers.DictField):
    pass


@extend_schema_serializer(component_name="ErrorDTO")
class ErrorOutput(serializers.Serializer[Any]):
    error = ErrorBodyField()


class AutoSchema(SpectacularAutoSchema):
    def get_operation(
        self,
        path: str,
        path_regex: str,
        path_prefix: str,
        method: str,
        registry: ComponentRegistry,
    ) -> dict[str, Any] | None:
        operation: dict[str, Any] | None = super().get_operation(
            path, path_regex, path_prefix, method, registry
        )
        if operation is None:
            return None

        ref = self.resolve_serializer(ErrorOutput, "response").ref
        responses: dict[str, Any] = operation["responses"]
        for code in self._default_error_codes(operation):
            responses.setdefault(code, _default_error_response(code, ref))
        if "429" in responses:
            responses["429"].setdefault("headers", {}).setdefault(
                "Retry-After", dict(RETRY_AFTER_HEADER)
            )
        # Thứ tự mã cố định để `openapi.yaml` không đổi giữa các lần sinh
        operation["responses"] = dict(sorted(responses.items()))
        return operation

    # `type: ignore[override]`: lớp gốc của DRF khai `get_description(path, method)`, còn
    # drf-spectacular gọi không tham số; `openapi.py` của upstream cũng ignore đúng chữ ký này
    def get_description(self) -> str:  # type: ignore[override]
        # Bỏ docstring của view; `extend_schema(description=…)` vẫn ghi đè được
        return ""

    def get_tags(self) -> list[str]:
        app_match = API_APP_PATH.match(self.path)
        package = type(self.view).__module__.split(".")
        if app_match is None or len(package) < 2 or package[0] not in _MODULE_PACKAGES:
            tags: list[str] = super().get_tags()
            return tags
        return [f"{app_match['app']} · {package[1]}"]

    def _map_basic_serializer(self, serializer: Any, direction: str) -> dict[str, Any]:
        schema: dict[str, Any] = super()._map_basic_serializer(serializer, direction)
        # Bỏ docstring của serializer; `extend_schema_serializer(description=…)` vẫn giữ
        if get_override(serializer, "description") is None:
            schema.pop("description", None)
        return schema

    def _default_error_codes(self, operation: dict[str, Any]) -> list[str]:
        codes = ["400", "500"]
        # Đối tượng theo path không tồn tại, hoặc trang vượt quá cuối của `StandardPagination`
        if any(
            param["in"] == "path"
            or (param["in"], param["name"]) == ("query", StandardPagination.page_query_param)
            for param in operation.get("parameters", [])
        ):
            codes.append("404")
        if self.view.get_throttles():
            codes.append("429")
        # Endpoint cần đăng nhập đọc trạng thái auth từ DB mỗi request (05 mục 2.2)
        if not all(isinstance(permission, AllowAny) for permission in self.view.get_permissions()):
            codes.extend(["401", "403", "503"])
        return codes


def _default_error_response(code: str, ref: dict[str, Any]) -> dict[str, Any]:
    error_code, message, details = _ERROR_EXAMPLES[code]
    example = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "request_id": EXAMPLE_REQUEST_ID,
        }
    }
    return {
        "content": {
            "application/json": {
                "schema": dict(ref),
                "examples": {error_code: {"value": example}},
            }
        },
        "description": ERROR_DESCRIPTIONS[code],
    }
