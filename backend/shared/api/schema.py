"""OpenAPI: component `ErrorDTO` và response lỗi mặc định cho mọi operation (04 mục 3, 5.1, 5.6).

`AutoSchema` là `DEFAULT_SCHEMA_CLASS`: thêm 400, 500 cho mọi operation, 429 khi view có
throttle, 404 khi path có tham số hoặc có query `page` của phân trang. View tự khai mã đặc thù
(409, 422…) bằng `extend_schema`; mã đã khai thì giữ nguyên. 401/403 thêm khi có JWT (M1).
"""

from typing import Any

from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.plumbing import ComponentRegistry
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from shared.api.pagination import StandardPagination

# Chuỗi thường, không dịch: schema sinh bằng CLI phải giống nhau ở mọi máy (12 mục 5)
ERROR_BODY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Mã lỗi ổn định, frontend dịch theo mã."},
        "message": {
            "type": "string",
            "description": "Thông báo mặc định theo `Accept-Language`.",
        },
        "details": {
            "type": "object",
            "additionalProperties": {},
            "description": (
                "Chi tiết theo mã. `VALIDATION_ERROR`: `{fields: {field_path: string[]}}`; "
                "mã không có chi tiết: `{}`."
            ),
        },
        "request_id": {"type": "string", "description": "Mã request để tra log."},
    },
    "required": ["code", "message", "details", "request_id"],
}

ERROR_DESCRIPTIONS = {
    "400": "Request không hợp lệ (`VALIDATION_ERROR`, `PARSE_ERROR`, `BAD_REQUEST`).",
    "404": "Không tìm thấy (`NOT_FOUND`).",
    "429": "Vượt giới hạn request (`THROTTLED`).",
    "500": "Lỗi hệ thống (`INTERNAL_ERROR`).",
}


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
            responses.setdefault(
                code,
                {
                    "content": {"application/json": {"schema": dict(ref)}},
                    "description": ERROR_DESCRIPTIONS[code],
                },
            )
        # Thứ tự mã cố định để `openapi.yaml` không đổi giữa các lần sinh
        operation["responses"] = dict(sorted(responses.items()))
        return operation

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
        return codes
