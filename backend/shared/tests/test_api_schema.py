"""OpenAPI sinh bằng `manage.py spectacular`: component `ErrorDTO`, response lỗi mặc định, tag,
content type, phần giới thiệu và tuỳ chọn Swagger UI (04 mục 3, 4.4, 5.1, 5.6)."""

from typing import Any

import pytest
import yaml
from django.core.management import call_command
from django.urls import path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.settings import spectacular_settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.exception_handler import error_body
from shared.api.schema import ERROR_DESCRIPTIONS, ErrorOutput
from tests.helpers import load_openapi_generator

ERROR_DTO_REF = {"$ref": "#/components/schemas/ErrorDTO"}
WARDS_PATH = "/api/v1/store/geo/provinces/{code}/wards"
PROVINCES_PATH = "/api/v1/store/geo/provinces"
LOGIN_PATH = "/api/v1/backoffice/auth/login"
ME_PATH = "/api/v1/backoffice/auth/me"
CUSTOM_NOT_FOUND_DESCRIPTION = "No variant with this SKU."
# Mã lỗi của ví dụ `ErrorDTO` chung mà `AutoSchema` gắn cho từng lỗi mặc định
DEFAULT_ERROR_EXAMPLE_CODES = {
    "400": "VALIDATION_ERROR",
    "401": "NOT_AUTHENTICATED",
    "403": "PERMISSION_DENIED",
    "404": "NOT_FOUND",
    "415": "UNSUPPORTED_MEDIA_TYPE",
    "429": "THROTTLED",
    "500": "INTERNAL_ERROR",
    "503": "AUTH_STATE_UNAVAILABLE",
}
# Mã lỗi view tự khai (ngoài lỗi mặc định của `AutoSchema`) và `code` của ví dụ `ErrorDTO`
DECLARED_ERROR_EXAMPLE_CODES = {f"POST {LOGIN_PATH}": {"401": "INVALID_CREDENTIALS"}}


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


def _api_operations(openapi: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (name, operation)
        for name, operation in _operations(openapi)
        if name.split(" ", 1)[1].startswith("/api/v1/")
    ]


def _json_examples(body: dict[str, Any]) -> dict[str, Any]:
    examples: dict[str, Any] = body["content"]["application/json"].get("examples", {})
    return examples


def _default_errors(openapi: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Response lỗi mặc định của `AutoSchema`: wards có 400/404/429/500, me có 401/403/503, login
    có 415 (401 của login do view tự khai nên không lấy)."""
    paths = openapi["paths"]
    wards = paths[WARDS_PATH]["get"]["responses"]
    me = paths[ME_PATH]["get"]["responses"]
    login = paths[LOGIN_PATH]["post"]["responses"]
    defaults = {
        code: response
        for responses in (wards, me)
        for code, response in responses.items()
        if code != "200"
    }
    return {**defaults, "415": login["415"]}


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


def test_tags_derive_from_app_and_module(
    schema: dict[str, Any], sample_schema: dict[str, Any]
) -> None:
    paths = schema["paths"]
    login_tags = paths[LOGIN_PATH]["post"]["tags"]
    me_tags = paths[ME_PATH]["get"]["tags"]
    provinces_tags = paths[PROVINCES_PATH]["get"]["tags"]
    wards_tags = paths[WARDS_PATH]["get"]["tags"]
    outside_api_tags = sample_schema["paths"]["/paged"]["get"]["tags"]

    assert login_tags == ["backoffice · identity"]
    assert me_tags == ["backoffice · identity"]
    assert provinces_tags == ["store · geo"]
    assert wards_tags == ["store · geo"]
    # Path ngoài `/api/v1/` giữ tag mặc định của drf-spectacular
    assert outside_api_tags == ["paged"]


def test_operation_with_request_body_declares_415(schema: dict[str, Any]) -> None:
    # Parser mặc định chỉ nhận JSON: body form hay multipart trả `415 UNSUPPORTED_MEDIA_TYPE`
    operations = _operations(schema)
    declares_415 = {name: "415" in operation["responses"] for name, operation in operations}
    has_body = {name: "requestBody" in operation for name, operation in operations}

    assert declares_415 == has_body
    assert declares_415[f"POST {LOGIN_PATH}"]


def test_json_operation_accepts_only_json(schema: dict[str, Any]) -> None:
    media_types = list(schema["paths"][LOGIN_PATH]["post"]["requestBody"]["content"])

    assert media_types == ["application/json"]


def test_throttled_response_declares_retry_after(
    schema: dict[str, Any], sample_schema: dict[str, Any]
) -> None:
    throttled = [
        (name, operation["responses"]["429"])
        for openapi in (schema, sample_schema)
        for name, operation in _operations(openapi)
        if "429" in operation["responses"]
    ]

    assert throttled
    for name, response in throttled:
        retry_after = response.get("headers", {}).get("Retry-After", {})
        assert retry_after.get("schema") == {"type": "integer"}, name


def test_default_errors_have_example_with_matching_code(schema: dict[str, Any]) -> None:
    # Tên ví dụ và `error.code` của nó, theo từng mã lỗi mặc định
    example_codes = {
        code: {
            name: example["value"]["error"]["code"]
            for name, example in _json_examples(response).items()
        }
        for code, response in _default_errors(schema).items()
    }
    expected = {code: {name: name} for code, name in DEFAULT_ERROR_EXAMPLE_CODES.items()}

    assert example_codes == expected


def test_default_error_examples_follow_error_dto(schema: dict[str, Any]) -> None:
    error_keys = set(error_body("X", "y")["error"])
    example_keys = {
        code: [set(example["value"]["error"]) for example in _json_examples(response).values()]
        for code, response in _default_errors(schema).items()
    }
    expected = {code: [error_keys] for code in DEFAULT_ERROR_EXAMPLE_CODES}

    assert example_keys == expected


def test_default_error_descriptions_name_their_code(schema: dict[str, Any]) -> None:
    unnamed = [
        code
        for code, response in _default_errors(schema).items()
        if f"`{DEFAULT_ERROR_EXAMPLE_CODES[code]}`" not in response["description"]
    ]

    assert unnamed == []


def test_default_errors_have_english_description_and_example(schema: dict[str, Any]) -> None:
    # Checker miễn `error.message` (message thật dịch theo `Accept-Language`), nhưng ví dụ chung là
    # dữ liệu giả tiếng Anh, kể cả message: kiểm thẳng chữ ASCII
    non_english = [
        code
        for code, response in _default_errors(schema).items()
        for text in [response["description"], *map(str, _json_examples(response).values())]
        if not text.isascii()
    ]

    assert non_english == []


def test_docstrings_are_not_in_schema(
    schema: dict[str, Any], sample_schema: dict[str, Any]
) -> None:
    described = [
        name
        for openapi in (schema, sample_schema)
        for name, operation in _operations(openapi)
        if "description" in operation
    ]
    account_dto = schema["components"]["schemas"]["AccountDTO"]

    assert described == []
    # `AccountOutput` có docstring tiếng Việt; component không lấy docstring làm mô tả
    assert "description" not in account_dto


def test_info_describes_apps_auth_errors_and_headers(schema: dict[str, Any]) -> None:
    description = schema["info"].get("description", "")

    for term in (
        "store",
        "backoffice",
        "BFF",
        "POST /api/v1/backoffice/auth/login",
        "Authorize",
        "ErrorDTO",
        "Accept-Language",
        "X-Request-ID",
        "Idempotency-Key",
    ):
        assert term in description, term
    assert description.isascii()
    # Không khai `servers`: Swagger gọi đúng host đang mở (local, staging)
    assert "servers" not in schema


def test_swagger_ui_settings_are_configured() -> None:
    ui_settings = spectacular_settings.SWAGGER_UI_SETTINGS

    assert ui_settings == {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "docExpansion": "none",
        "deepLinking": True,
    }


def test_current_operations_have_summary_and_examples(schema: dict[str, Any]) -> None:
    # Luật chú thích của `gen_openapi.py --check` (04 mục 5.6) trên schema thật: summary, ví dụ
    # request/2xx/lỗi tự khai, tag và chữ tiếng Anh
    operation_names = sorted(name for name, _ in _api_operations(schema))
    violations = load_openapi_generator().quality_violations(schema, ERROR_DESCRIPTIONS)

    assert operation_names == sorted(
        [f"POST {LOGIN_PATH}", f"GET {ME_PATH}", f"GET {PROVINCES_PATH}", f"GET {WARDS_PATH}"]
    )
    assert violations == []


def test_declared_errors_have_examples_with_matching_code(schema: dict[str, Any]) -> None:
    operations = dict(_api_operations(schema))
    error_keys = set(error_body("X", "y")["error"])

    for name, declared in DECLARED_ERROR_EXAMPLE_CODES.items():
        for code, error_code in declared.items():
            response = operations[name]["responses"][code]
            # Tên ví dụ do drf-spectacular camelize nên kiểm theo `error.code` của giá trị
            errors = [example["value"]["error"] for example in _json_examples(response).values()]
            error_codes = [error["code"] for error in errors]
            assert error_codes == [error_code], f"{name} {code}"
            assert set(errors[0]) == error_keys, f"{name} {code}"
            assert f"`{error_code}`" in response["description"], f"{name} {code}"
