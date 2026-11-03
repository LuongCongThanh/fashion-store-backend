"""Kiểm `scripts/gen_openapi.py`: schema lệch hoặc sai chuẩn thì `--check` fail (12 mục 5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import BACKEND, isolated_env

GENERATOR = BACKEND / "scripts/gen_openapi.py"
GENERATION_FAILED = "drf-spectacular failed to generate a valid schema"
PREVIOUS_SCHEMA = "openapi: 3.0.3\n"


def _generate(
    schema: Path, *options: str, settings: str = "config.settings.test", pythonpath: str = ""
) -> subprocess.CompletedProcess[str]:
    env = {**isolated_env(), "DJANGO_SETTINGS_MODULE": settings}
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GENERATOR), "--schema", str(schema), *options],
        cwd=BACKEND,
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
    schema = tmp_path_factory.mktemp("openapi") / "openapi.yaml"
    result = _generate(schema)
    assert result.returncode == 0, result.stdout + result.stderr
    return schema.read_text(encoding="utf-8")


def test_check_fails_when_committed_schema_is_stale(tmp_path: Path, current_schema: str) -> None:
    edited = current_schema.replace("title: Fashion Store API", "title: Stale API", 1)
    assert edited != current_schema
    schema = tmp_path / "openapi.yaml"
    schema.write_text(edited, encoding="utf-8", newline="\n")

    result = _generate(schema, "--check")

    assert result.returncode == 1
    assert "make openapi" in result.stdout


def test_check_passes_when_schema_is_current(tmp_path: Path, current_schema: str) -> None:
    schema = tmp_path / "openapi.yaml"
    schema.write_text(current_schema, encoding="utf-8", newline="\n")

    result = _generate(schema, "--check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_generation_fails_when_schema_is_invalid(tmp_path: Path) -> None:
    # `info.version` phải là chuỗi theo chuẩn OpenAPI 3.0: `--validate` báo lỗi
    settings = _write_settings(
        tmp_path, "SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, 'VERSION': 1}  # noqa: F405\n"
    )
    schema = tmp_path / "openapi.yaml"
    schema.write_text(PREVIOUS_SCHEMA, encoding="utf-8")

    result = _generate(schema, settings=settings, pythonpath=str(tmp_path))

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

    result = _generate(schema, settings=settings, pythonpath=str(tmp_path))

    assert result.returncode == 1
    assert GENERATION_FAILED in result.stderr
    assert schema.read_text(encoding="utf-8") == PREVIOUS_SCHEMA


def test_check_rejects_non_utf8_schema(tmp_path: Path) -> None:
    schema = tmp_path / "openapi.yaml"
    schema.write_bytes(b"title: \xff\n")

    result = _generate(schema, "--check")

    assert result.returncode == 2
    assert "ERROR" in result.stderr
