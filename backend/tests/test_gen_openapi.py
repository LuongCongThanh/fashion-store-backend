"""Kiểm `scripts/gen_openapi.py`: schema lệch hoặc sai chuẩn thì `--check` fail (12 mục 5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.helpers import BACKEND, isolated_env

GENERATOR = BACKEND / "scripts/gen_openapi.py"


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


def test_check_fails_when_committed_schema_is_stale(tmp_path: Path) -> None:
    schema = tmp_path / "openapi.yaml"
    assert _generate(schema).returncode == 0
    text = schema.read_text(encoding="utf-8")
    edited = text.replace("title: Fashion Store API", "title: Stale API", 1)
    assert edited != text
    schema.write_text(edited, encoding="utf-8", newline="\n")

    result = _generate(schema, "--check")

    assert result.returncode == 1
    assert "make openapi" in result.stdout


def test_check_passes_when_schema_is_current(tmp_path: Path) -> None:
    schema = tmp_path / "openapi.yaml"
    assert _generate(schema).returncode == 0

    result = _generate(schema, "--check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_generation_fails_when_schema_is_invalid(tmp_path: Path) -> None:
    # `info.version` phải là chuỗi theo chuẩn OpenAPI 3.0: `--validate` báo lỗi
    (tmp_path / "invalid_schema_settings.py").write_text(
        "from config.settings.test import *  # noqa: F403\n"
        "SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, 'VERSION': 1}  # noqa: F405\n",
        encoding="utf-8",
    )
    schema = tmp_path / "openapi.yaml"
    schema.write_text("", encoding="utf-8")

    result = _generate(
        schema, "--check", settings="invalid_schema_settings", pythonpath=str(tmp_path)
    )

    assert result.returncode == 1
    assert "info" in result.stderr
