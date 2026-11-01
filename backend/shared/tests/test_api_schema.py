"""OpenAPI sinh bằng `manage.py spectacular`: component `ErrorDTO` và response lỗi mặc định
(04 mục 3, 5.1, 5.6)."""

from typing import Any

import pytest
import yaml
from django.core.management import call_command
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.exception_handler import error_body
from shared.api.schema import ErrorOutput

ERROR_DTO_REF = {"$ref": "#/components/schemas/ErrorDTO"}
WARDS_PATH = "/api/v1/store/geo/provinces/{code}/wards"
PROVINCES_PATH = "/api/v1/store/geo/provinces"
CUSTOM_NOT_FOUND_DESCRIPTION = "Không có sản phẩm với mã này."


class ItemOutput(serializers.Serializer[Any]):
    code = serializers.CharField()


class PagedView(ListAPIView[Any]):
    """List phân trang bằng `DEFAULT_PAGINATION_CLASS`, throttle mặc định."""

    permission_classes = (AllowAny,)
    serializer_class = ItemOutput


class UnthrottledView(ListAPIView[Any]):
    """List không phân trang, không throttle: chỉ trả được 400 và 500."""

    permission_classes = (AllowAny,)
    pagination_class = None
    throttle_classes = ()
    serializer_class = ItemOutput


class CustomNotFoundView(APIView):
    """View tự khai 404 với mô tả riêng, khai trước 200 để kiểm thứ tự sau khi gộp."""

    permission_classes = (AllowAny,)

    @extend_schema(
        parameters=[OpenApiParameter("code", str, OpenApiParameter.PATH)],
        responses={
            404: OpenApiResponse(ErrorOutput, description=CUSTOM_NOT_FOUND_DESCRIPTION),
            200: ItemOutput,
        },
    )
    def get(self, request: Request, code: str) -> Response:
        return Response({"code": code})


# Endpoint thật (geo) không có view phân trang, view không throttle hay view tự khai 404,
# nên sinh schema riêng cho các view mẫu này
SAMPLE_PATTERNS = [
    path("paged", PagedView.as_view()),
    path("unthrottled", UnthrottledView.as_view()),
    path("custom/<str:code>", CustomNotFoundView.as_view()),
]


@pytest.fixture(scope="module")
def schema(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    file = tmp_path_factory.mktemp("openapi") / "openapi.yaml"
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(file))
    loaded: dict[str, Any] = yaml.safe_load(file.read_text(encoding="utf-8"))
    return loaded


@pytest.fixture(scope="module")
def sample_schema() -> dict[str, Any]:
    generated: dict[str, Any] = SchemaGenerator(patterns=SAMPLE_PATTERNS).get_schema(
        request=None, public=True
    )
    return generated


def _operations(openapi: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"{method.upper()} {path}", operation)
        for path, item in openapi["paths"].items()
        for method, operation in item.items()
    ]


def _json_schema_of(response: dict[str, Any]) -> dict[str, Any]:
    json_schema: dict[str, Any] = response["content"]["application/json"]["schema"]
    return json_schema


def test_schema_has_error_dto_component(schema: dict[str, Any]) -> None:
    error_dto = schema["components"]["schemas"]["ErrorDTO"]
    body = error_dto["properties"]["error"]

    assert error_dto["required"] == ["error"]
    assert body["type"] == "object"
    assert body["required"] == ["code", "message", "details", "request_id"]
    assert body["properties"]["code"]["type"] == "string"
    assert body["properties"]["message"]["type"] == "string"
    assert body["properties"]["details"]["type"] == "object"
    assert body["properties"]["details"]["additionalProperties"] == {}
    assert body["properties"]["request_id"]["type"] == "string"


def test_error_dto_keys_match_error_body(schema: dict[str, Any]) -> None:
    body = schema["components"]["schemas"]["ErrorDTO"]["properties"]["error"]
    keys = set(error_body("X", "y")["error"])

    assert keys == set(body["required"])


def test_every_operation_declares_common_errors(schema: dict[str, Any]) -> None:
    operations = _operations(schema)

    assert operations
    for name, operation in operations:
        responses = operation["responses"]
        for code in ("400", "500"):
            assert _json_schema_of(responses[code]) == ERROR_DTO_REF, f"{name} {code}"
        codes = list(responses)
        assert codes == sorted(responses), name


def test_geo_operations_declare_exact_error_codes(schema: dict[str, Any]) -> None:
    wards = schema["paths"][WARDS_PATH]["get"]["responses"]
    provinces = schema["paths"][PROVINCES_PATH]["get"]["responses"]
    wards_codes = list(wards)
    provinces_codes = list(provinces)

    assert wards_codes == ["200", "400", "404", "429", "500"]
    assert provinces_codes == ["200", "400", "429", "500"]
    assert _json_schema_of(wards["404"]) == ERROR_DTO_REF
    assert _json_schema_of(wards["429"]) == ERROR_DTO_REF


def test_paginated_operation_declares_404(sample_schema: dict[str, Any]) -> None:
    responses = sample_schema["paths"]["/paged"]["get"]["responses"]
    codes = list(responses)

    assert codes == ["200", "400", "404", "429", "500"]
    assert _json_schema_of(responses["404"]) == ERROR_DTO_REF


def test_operation_without_throttle_omits_429(sample_schema: dict[str, Any]) -> None:
    responses = sample_schema["paths"]["/unthrottled"]["get"]["responses"]
    codes = list(responses)

    assert codes == ["200", "400", "500"]


def test_declared_error_response_is_kept(sample_schema: dict[str, Any]) -> None:
    responses = sample_schema["paths"]["/custom/{code}"]["get"]["responses"]
    codes = list(responses)

    assert codes == ["200", "400", "404", "429", "500"]
    assert responses["404"]["description"] == CUSTOM_NOT_FOUND_DESCRIPTION
    assert _json_schema_of(responses["404"]) == ERROR_DTO_REF
