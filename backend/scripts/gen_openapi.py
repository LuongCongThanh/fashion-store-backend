"""Sinh lại `openapi.yaml` bằng drf-spectacular, hoặc chỉ kiểm file đã commit với `--check`.

Schema là hợp đồng với frontend (12 mục 5): mọi thay đổi API phải hiện trong diff của PR.
`--check` còn chạy luật chú thích của 04 mục 5.6 (summary, ví dụ, tag, chữ tiếng Anh) trên schema
vừa sinh, nên operation mới thiếu chú thích làm `make lint` fail.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

BACKEND = Path(__file__).resolve().parents[1]
SCHEMA_NAME = "openapi.yaml"
_API_PREFIX = "/api/v1/"
# Chữ tiếng Việt có dấu: chữ hiển thị trên Swagger viết tiếng Anh (04 mục 5.6)
_VIETNAMESE_LETTERS = re.compile(
    "[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)


class GeneratorError(Exception):
    """File schema hiện có không đọc được."""


def _render(target: Path) -> int:
    """Ghi schema vào `target`; trả exit code của `manage.py spectacular`.

    `--fail-on-warn`: warning (serializer không đoán được, enum trùng tên) làm schema thiếu mà
    lệnh vẫn exit 0. Lỗi của spectacular in thẳng ra stderr của script.
    """
    command = [
        sys.executable,
        "manage.py",
        "spectacular",
        "--validate",
        "--fail-on-warn",
        "--file",
        str(target),
    ]
    # manage.py mặc định settings `local`; dùng `test` như pytest, mypy và CI để schema sinh trên
    # máy trùng với schema CI kiểm
    env = {**os.environ}
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    # S603: Python, manage.py và tham số cố định, không qua shell. Lý do ghi ở dòng riêng vì
    # SonarCloud cũng đọc chỉ thị noqa và coi phần chữ phía sau là sai cú pháp
    return subprocess.run(command, cwd=BACKEND, env=env, check=False).returncode  # noqa: S603


def _default_error_descriptions() -> dict[str, str]:
    """Mô tả lỗi mặc định lấy từ `shared.api.schema`, với cùng settings như `_render`."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    # Import muộn: `shared.api.schema` cần Django đã setup, còn chế độ sinh file không cần
    import django

    django.setup()
    from shared.api.schema import ERROR_DESCRIPTIONS

    return dict(ERROR_DESCRIPTIONS)


def quality_violations(
    openapi: Mapping[str, Any], default_error_descriptions: Mapping[str, str]
) -> list[str]:
    """Luật chú thích của 04 mục 5.6 trên schema đã render; mỗi vi phạm là
    `<operationId>: <thiếu gì>`.

    `default_error_descriptions` là mô tả lỗi mặc định của `AutoSchema`: response lỗi mang đúng mô
    tả đó đã có ví dụ chung, còn mã view tự khai (mô tả khác) phải có ví dụ `ErrorDTO` riêng.
    Đánh đổi: lỗi mặc định nhận diện bằng mô tả trùng `ERROR_DESCRIPTIONS`, nên view khai lại một mã
    lỗi mặc định với đúng mô tả đó mà không có ví dụ riêng thì luật 4 không bắt được.

    Cần Django đã setup (như `_default_error_descriptions`): ứng dụng của path lấy từ
    `shared.api.schema.API_APP_PATH`.
    """
    violations: list[str] = []
    for path, item in openapi.get("paths", {}).items():
        # Chỉ operation của API (`/api/v1/`) bắt buộc chú thích; schema, docs được miễn
        if not path.startswith(_API_PREFIX):
            continue
        for method, operation in item.items():
            operation_label = operation.get("operationId") or f"{method.upper()} {path}"
            violations.extend(
                f"{operation_label}: {problem}"
                for problem in _operation_problems(path, operation, default_error_descriptions)
            )
    return violations


def _operation_problems(
    path: str, operation: Mapping[str, Any], default_error_descriptions: Mapping[str, str]
) -> list[str]:
    problems: list[str] = []
    if not operation.get("summary"):
        problems.append("missing summary")
    request = operation.get("requestBody")
    if request is not None and not _examples(request):
        problems.append("missing request example")
    for code, response in operation.get("responses", {}).items():
        if code.startswith("2"):
            if response.get("content") and not _examples(response):
                problems.append(f"missing example for {code} response")
        # Lỗi mặc định đã có ví dụ chung của `AutoSchema`; mã view tự khai có mô tả riêng
        elif code[0] in "45" and response.get("description") != default_error_descriptions.get(
            code
        ):
            problems.extend(_declared_error_problems(code, response))
    # Import muộn như `_default_error_descriptions`: `shared.api.schema` cần Django đã setup.
    # Dùng chung regex với `AutoSchema.get_tags` để luật tag không lệch với tag được sinh
    from shared.api.schema import API_APP_PATH

    app_match = API_APP_PATH.match(path)
    app = app_match["app"] if app_match else "<store|backoffice>"
    tag_format = re.compile(rf"{re.escape(app)} · [a-z][a-z0-9_]*")
    problems.extend(
        f"tag '{tag}' is not '{app} · <module>'"
        for tag in operation.get("tags") or [""]
        if not tag_format.fullmatch(tag)
    )
    problems.extend(
        f"Vietnamese text in {where}"
        for where, text in _shown_texts(operation)
        if _VIETNAMESE_LETTERS.search(text)
    )
    return problems


def _declared_error_problems(code: str, response: Mapping[str, Any]) -> list[str]:
    # Tên ví dụ bị drf-spectacular camelize, nên nhận ví dụ `ErrorDTO` theo `error.code` của giá trị
    # Giá trị không có `error` dạng object (không phải `ErrorDTO`) bị bỏ qua như
    # `_without_error_message`, để thành vi phạm thiếu ví dụ thay vì làm script crash
    example_values = [example.get("value") for example in _examples(response).values()]
    errors = [
        value["error"]
        for value in example_values
        if isinstance(value, Mapping) and isinstance(value.get("error"), Mapping)
    ]
    error_codes = [error["code"] for error in errors if "code" in error]
    if not error_codes:
        return [f"missing ErrorDTO example for {code} response"]
    description = response.get("description", "")
    return [
        f"{code} example code {error_code} is not in the response description"
        for error_code in error_codes
        if f"`{error_code}`" not in description
    ]


def _examples(body: Mapping[str, Any]) -> dict[str, Any]:
    """Ví dụ của mọi media type trong `content` của request/response."""
    return {
        name: example
        for media in body.get("content", {}).values()
        for name, example in media.get("examples", {}).items()
    }


def _shown_texts(operation: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Chữ Swagger hiển thị kèm vị trí: summary, description và ví dụ."""
    texts = [
        ("summary", operation.get("summary", "")),
        ("description", operation.get("description", "")),
    ]
    request = operation.get("requestBody", {})
    texts.append(("request description", request.get("description", "")))
    texts.extend(("request example", str(example)) for example in _examples(request).values())
    for code, response in operation.get("responses", {}).items():
        texts.append((f"{code} response description", response.get("description", "")))
        # Chỉ ví dụ lỗi (4xx/5xx) được miễn `error.message`; ví dụ 2xx kiểm nguyên văn
        is_error = code[0] in "45"
        texts.extend(
            (
                f"{code} response example",
                str(_without_error_message(example) if is_error else example),
            )
            for example in _examples(response).values()
        )
    return texts


def _without_error_message(example: Mapping[str, Any]) -> Mapping[str, Any]:
    """Bỏ `error.message` của ví dụ `ErrorDTO`: message dịch theo `Accept-Language`, mặc định
    `vi`, nên được phép là tiếng Việt."""
    value = example.get("value")
    if not isinstance(value, Mapping) or not isinstance(value.get("error"), Mapping):
        return example
    return {**example, "value": {**value, "error": {**value["error"], "message": ""}}}


def _run(schema: Path, *, check: bool) -> int:
    if not check:
        # spectacular chỉ ghi file khi đã sinh và kiểm xong: lỗi thì file đã commit giữ nguyên
        return _report_failure() if _render(schema) != 0 else 0
    with tempfile.TemporaryDirectory() as tmp:
        generated = Path(tmp) / SCHEMA_NAME
        if _render(generated) != 0:
            return _report_failure()
        expected = generated.read_text(encoding="utf-8")
    # Luật chú thích chạy trước bước so drift: vi phạm in ra dù file đã commit trùng hay lệch
    violations = quality_violations(yaml.safe_load(expected), _default_error_descriptions())
    for violation in violations:
        print(violation)
    drift = _report_drift(schema, expected)
    return 1 if violations or drift else 0


def _report_drift(schema: Path, expected: str) -> bool:
    """In diff khi `schema` lệch với schema vừa sinh; trả True nếu lệch."""
    try:
        current = schema.read_text(encoding="utf-8") if schema.exists() else ""
    except UnicodeDecodeError as exc:
        raise GeneratorError(f"{schema}: {exc}") from exc
    if current == expected:
        return False
    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=schema.name,
        tofile="manage.py spectacular",
    )
    sys.stdout.writelines(diff)
    print(f"{schema.name} is stale: run `make openapi` and commit the result")
    return True


def _report_failure() -> int:
    print("ERROR: drf-spectacular failed to generate a valid schema", file=sys.stderr)
    return 1


def main() -> int:
    """Sinh lại `openapi.yaml`, hoặc với `--check` kiểm luật chú thích và báo lệch (không ghi)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="check annotation rules and report drift, do not write"
    )
    args = parser.parse_args()
    try:
        # Luôn dùng `openapi.yaml` của thư mục hiện tại (`backend/` ở Make và CI), như
        # gen_importlinter.py: không nhận đường dẫn từ CLI
        return _run(Path.cwd() / SCHEMA_NAME, check=args.check)
    except (GeneratorError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
