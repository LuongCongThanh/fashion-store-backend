"""Kiểm `scripts/gen_openapi.py`: schema lệch hoặc sai chuẩn thì `--check` fail (12 mục 5)."""

from __future__ import annotations

import copy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from shared.api.schema import ERROR_DESCRIPTIONS
from tests.helpers import OPENAPI_GENERATOR, isolated_env, load_openapi_generator

GENERATION_FAILED = "drf-spectacular failed to generate a valid schema"
PREVIOUS_SCHEMA = "openapi: 3.0.3\n"
OPERATION_ID = "v1_store_catalog_products_create"
PRODUCTS_PATH = "/api/v1/store/catalog/products"


def _generate(
    root: Path, *options: str, settings: str = "config.settings.test", pythonpath: str = ""
) -> subprocess.CompletedProcess[str]:
    """Chạy script với `root` là thư mục hiện tại: script đọc và ghi `root/openapi.yaml`."""
    env = {**isolated_env(), "DJANGO_SETTINGS_MODULE": settings}
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(OPENAPI_GENERATOR), *options],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _write_settings(root: Path, overrides: str) -> str:
    """Ghi module settings tạm kế thừa `config.settings.test`, trả tên module."""
    (root / "override_settings.py").write_text(
        "from config.settings.test import *  # noqa: F403\n" + overrides, encoding="utf-8"
    )
    return "override_settings"


@pytest.fixture(scope="module")
def current_schema(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Schema sinh từ code hiện tại, dùng chung để mỗi test không phải khởi động Django lại."""
    root = tmp_path_factory.mktemp("openapi")
    result = _generate(root)
    assert result.returncode == 0, result.stdout + result.stderr
    return (root / "openapi.yaml").read_text(encoding="utf-8")


def test_check_fails_when_committed_schema_is_stale(tmp_path: Path, current_schema: str) -> None:
    edited = current_schema.replace("title: Fashion Store API", "title: Stale API", 1)
    assert edited != current_schema
    schema = tmp_path / "openapi.yaml"
    schema.write_text(edited, encoding="utf-8", newline="\n")

    result = _generate(tmp_path, "--check")

    assert result.returncode == 1
    assert "make openapi" in result.stdout


def test_check_passes_when_schema_is_current(tmp_path: Path, current_schema: str) -> None:
    schema = tmp_path / "openapi.yaml"
    schema.write_text(current_schema, encoding="utf-8", newline="\n")

    result = _generate(tmp_path, "--check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_generation_fails_when_schema_is_invalid(tmp_path: Path) -> None:
    # `info.version` phải là chuỗi theo chuẩn OpenAPI 3.0: `--validate` báo lỗi
    settings = _write_settings(
        tmp_path, "SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, 'VERSION': 1}  # noqa: F405\n"
    )
    schema = tmp_path / "openapi.yaml"
    schema.write_text(PREVIOUS_SCHEMA, encoding="utf-8")

    result = _generate(tmp_path, settings=settings, pythonpath=str(tmp_path))

    assert result.returncode == 1
    assert GENERATION_FAILED in result.stderr
    assert schema.read_text(encoding="utf-8") == PREVIOUS_SCHEMA


def test_generation_fails_on_spectacular_warning(tmp_path: Path) -> None:
    # APIView không khai serializer: spectacular chỉ cảnh báo, `--fail-on-warn` biến thành lỗi
    (tmp_path / "warning_urls.py").write_text(
        "from django.urls import path\n"
        "from rest_framework.views import APIView\n\n\n"
        "class NoSerializerView(APIView):\n"
        "    def get(self, request):\n"
        "        return None\n\n\n"
        'urlpatterns = [path("no-serializer", NoSerializerView.as_view())]\n',
        encoding="utf-8",
    )
    settings = _write_settings(tmp_path, 'ROOT_URLCONF = "warning_urls"\n')
    schema = tmp_path / "openapi.yaml"
    schema.write_text(PREVIOUS_SCHEMA, encoding="utf-8")

    result = _generate(tmp_path, settings=settings, pythonpath=str(tmp_path))

    assert result.returncode == 1
    assert GENERATION_FAILED in result.stderr
    assert schema.read_text(encoding="utf-8") == PREVIOUS_SCHEMA


def test_check_rejects_non_utf8_schema(tmp_path: Path) -> None:
    schema = tmp_path / "openapi.yaml"
    schema.write_bytes(b"title: \xff\n")

    result = _generate(tmp_path, "--check")

    assert result.returncode == 2
    assert "ERROR" in result.stderr


def _json_body(examples: dict[str, Any] | None = None, *, description: str = "") -> dict[str, Any]:
    media: dict[str, Any] = {"schema": {"type": "object"}}
    if examples is not None:
        media["examples"] = examples
    return {"content": {"application/json": media}, "description": description}


def _error_example(code: str, message: str = "SKU is already taken.") -> dict[str, Any]:
    return {
        "value": {"error": {"code": code, "message": message, "details": {}, "request_id": "req-1"}}
    }


def _annotated_schema() -> dict[str, Any]:
    """Schema một operation đủ chú thích: 400 mặc định không ví dụ, 409 view tự khai có ví dụ."""
    operation = {
        "operationId": OPERATION_ID,
        "summary": "Create a product",
        "tags": ["store · catalog"],
        "requestBody": _json_body({"LinenShirt": {"value": {"name": "Linen shirt"}}}),
        "responses": {
            "201": _json_body({"Product": {"value": {"code": "SKU-1", "name": "Linen shirt"}}}),
            "400": _json_body(description=ERROR_DESCRIPTIONS["400"]),
            "409": _json_body(
                {"SkuTaken": _error_example("SKU_TAKEN")},
                description="SKU already exists (`SKU_TAKEN`).",
            ),
        },
    }
    return {"openapi": "3.0.3", "paths": {PRODUCTS_PATH: {"post": operation}}}


def _operation(openapi: dict[str, Any]) -> dict[str, Any]:
    operation: dict[str, Any] = openapi["paths"][PRODUCTS_PATH]["post"]
    return operation


def _drop_summary(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["summary"]


def _drop_request_example(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["requestBody"]["content"]["application/json"]["examples"]


def _drop_success_example(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["responses"]["201"]["content"]["application/json"]["examples"]


def _drop_declared_error_example(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["responses"]["409"]["content"]["application/json"]["examples"]


def _mismatch_declared_error_code(openapi: dict[str, Any]) -> None:
    examples = {"Conflict": _error_example("CONFLICT")}
    _operation(openapi)["responses"]["409"]["content"]["application/json"]["examples"] = examples


def _declare_error_without_error_dto(openapi: dict[str, Any]) -> None:
    # Ví dụ không theo dạng `ErrorDTO` (thiếu key `error`) thì coi như chưa có ví dụ lỗi
    examples = {"Conflict": {"value": {"detail": "SKU is already taken."}}}
    _operation(openapi)["responses"]["409"]["content"]["application/json"]["examples"] = examples


def _redeclare_default_error(openapi: dict[str, Any]) -> None:
    # View khai lại 400 với mô tả riêng thì không còn là lỗi mặc định của `AutoSchema`
    _operation(openapi)["responses"]["400"]["description"] = "Size is not available (`BAD_SIZE`)."


def _untag_module(openapi: dict[str, Any]) -> None:
    _operation(openapi)["tags"] = ["catalog"]


def _drop_tags(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["tags"]


def _tag_other_app(openapi: dict[str, Any]) -> None:
    _operation(openapi)["tags"] = ["backoffice · catalog"]


def _vietnamese_summary(openapi: dict[str, Any]) -> None:
    _operation(openapi)["summary"] = "Tạo sản phẩm"


def _vietnamese_example(openapi: dict[str, Any]) -> None:
    examples = {"LinenShirt": {"value": {"name": "Áo sơ mi linen"}}}
    _operation(openapi)["requestBody"]["content"]["application/json"]["examples"] = examples


def _vietnamese_description(openapi: dict[str, Any]) -> None:
    _operation(openapi)["description"] = "Tạo sản phẩm mới trong danh mục."


def _vietnamese_response_description(openapi: dict[str, Any]) -> None:
    _operation(openapi)["responses"]["201"]["description"] = "Sản phẩm vừa tạo"


def _vietnamese_success_example(openapi: dict[str, Any]) -> None:
    examples = {"Product": {"value": {"code": "SKU-1", "name": "Áo sơ mi linen"}}}
    _operation(openapi)["responses"]["201"]["content"]["application/json"]["examples"] = examples


def _vietnamese_message_in_success_example(openapi: dict[str, Any]) -> None:
    # Miễn `error.message` chỉ áp cho ví dụ lỗi; ví dụ 2xx dạng `{"error": …}` vẫn bị kiểm
    examples = {"Product": _error_example("SKU_TAKEN", "Mã SKU đã tồn tại.")}
    _operation(openapi)["responses"]["201"]["content"]["application/json"]["examples"] = examples


def _vietnamese_parameter_description(openapi: dict[str, Any]) -> None:
    parameter = {"in": "query", "name": "size", "schema": {"type": "string"}, "description": "Cỡ"}
    _operation(openapi)["parameters"] = [parameter]


@pytest.mark.parametrize(
    ("mutate", "violation"),
    [
        pytest.param(_drop_summary, "missing summary", id="1-summary"),
        pytest.param(_drop_request_example, "missing request example", id="2-request-example"),
        pytest.param(_drop_success_example, "missing example for 201 response", id="3-2xx-example"),
        pytest.param(
            _drop_declared_error_example,
            "missing ErrorDTO example for 409 response",
            id="4-declared-error-example",
        ),
        pytest.param(
            _mismatch_declared_error_code,
            "409 example code CONFLICT is not in the response description",
            id="4-declared-error-code",
        ),
        pytest.param(
            _declare_error_without_error_dto,
            "missing ErrorDTO example for 409 response",
            id="4-declared-error-not-error-dto",
        ),
        pytest.param(
            _redeclare_default_error,
            "missing ErrorDTO example for 400 response",
            id="5-redeclared-default-error",
        ),
        pytest.param(_untag_module, "tag 'catalog' is not 'store · <module>'", id="6-tag-format"),
        pytest.param(
            _tag_other_app,
            "tag 'backoffice · catalog' is not 'store · <module>'",
            id="6-tag-app",
        ),
        pytest.param(_drop_tags, "tag '' is not 'store · <module>'", id="6-no-tag"),
        pytest.param(_vietnamese_summary, "Vietnamese text in summary", id="7-summary"),
        pytest.param(_vietnamese_example, "Vietnamese text in request example", id="7-example"),
        pytest.param(_vietnamese_description, "Vietnamese text in description", id="7-description"),
        pytest.param(
            _vietnamese_response_description,
            "Vietnamese text in 201 response description",
            id="7-response-description",
        ),
        pytest.param(
            _vietnamese_success_example,
            "Vietnamese text in 201 response example",
            id="7-2xx-example",
        ),
        pytest.param(
            _vietnamese_parameter_description,
            "Vietnamese text in parameter size description",
            id="7-parameter-description",
        ),
        pytest.param(
            _vietnamese_message_in_success_example,
            "Vietnamese text in 201 response example",
            id="7-2xx-error-shaped-example",
        ),
    ],
)
def test_quality_rule_reports_violation(
    mutate: Callable[[dict[str, Any]], None], violation: str
) -> None:
    openapi = copy.deepcopy(_annotated_schema())
    mutate(openapi)

    violations = load_openapi_generator().quality_violations(openapi, ERROR_DESCRIPTIONS)

    assert violations == [f"{OPERATION_ID}: {violation}"]


def _keep_annotated(openapi: dict[str, Any]) -> None:
    """Operation đủ chú thích, lỗi 400 mặc định không có ví dụ riêng."""


def _drop_request_body(openapi: dict[str, Any]) -> None:
    del _operation(openapi)["requestBody"]


def _respond_without_content(openapi: dict[str, Any]) -> None:
    responses = _operation(openapi)["responses"]
    del responses["201"]
    responses["204"] = {"description": "No response body"}


def _move_outside_api(openapi: dict[str, Any]) -> None:
    operation = openapi["paths"].pop(PRODUCTS_PATH)
    operation["post"]["tags"] = ["schema"]
    openapi["paths"]["/api/schema/"] = operation


def _vietnamese_error_message(openapi: dict[str, Any]) -> None:
    # `message` của ErrorDTO dịch theo `Accept-Language`, mặc định `vi`
    examples = {"SkuTaken": _error_example("SKU_TAKEN", "Mã SKU đã tồn tại.")}
    _operation(openapi)["responses"]["409"]["content"]["application/json"]["examples"] = examples


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(_keep_annotated, id="1-4-5-annotated"),
        pytest.param(_drop_request_body, id="2-no-request-body"),
        pytest.param(_respond_without_content, id="3-2xx-without-body"),
        pytest.param(_move_outside_api, id="6-outside-api-v1"),
        pytest.param(_vietnamese_error_message, id="7-error-message"),
    ],
)
def test_quality_rule_passes_annotated_operation(mutate: Callable[[dict[str, Any]], None]) -> None:
    openapi = copy.deepcopy(_annotated_schema())
    mutate(openapi)

    violations = load_openapi_generator().quality_violations(openapi, ERROR_DESCRIPTIONS)

    assert violations == []


def _product_component(field_description: str) -> dict[str, Any]:
    return {
        "type": "object",
        "description": "A product in the catalog.",
        "properties": {
            "name": {"type": "string", "description": "Display name."},
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"size": {"type": "string", "description": field_description}},
                },
            },
        },
    }


def test_quality_rule_reports_vietnamese_component_description() -> None:
    # Mô tả field lấy từ `help_text` của serializer, hiện ở mọi operation dùng component
    openapi = copy.deepcopy(_annotated_schema())
    openapi["components"] = {"schemas": {"Product": _product_component("Cỡ của biến thể")}}

    violations = load_openapi_generator().quality_violations(openapi, ERROR_DESCRIPTIONS)

    assert violations == ["Product: Vietnamese text in description of variants.items.size"]


def test_quality_rule_passes_english_component_description() -> None:
    openapi = copy.deepcopy(_annotated_schema())
    openapi["components"] = {"schemas": {"Product": _product_component("Variant size.")}}

    violations = load_openapi_generator().quality_violations(openapi, ERROR_DESCRIPTIONS)

    assert violations == []


def test_check_reports_quality_violation_from_rendered_schema(tmp_path: Path) -> None:
    # View hợp lệ với drf-spectacular (không warning) nhưng thiếu `summary`
    (tmp_path / "quality_urls.py").write_text(
        "from django.urls import path\n"
        "from drf_spectacular.utils import extend_schema\n"
        "from rest_framework.permissions import AllowAny\n"
        "from rest_framework.views import APIView\n\n\n"
        "class PingView(APIView):\n"
        "    permission_classes = [AllowAny]\n\n"
        "    @extend_schema(responses={204: None})\n"
        "    def get(self, request):\n"
        "        return None\n\n\n"
        'urlpatterns = [path("api/v1/store/ping", PingView.as_view())]\n',
        encoding="utf-8",
    )
    settings = _write_settings(tmp_path, 'ROOT_URLCONF = "quality_urls"\n')

    result = _generate(tmp_path, "--check", settings=settings, pythonpath=str(tmp_path))

    assert result.returncode == 1
    assert "api_v1_store_ping_retrieve: missing summary" in result.stdout.splitlines()
