"""Sinh lại `openapi.yaml` bằng drf-spectacular, hoặc chỉ kiểm file đã commit với `--check`.

Schema là hợp đồng với frontend (12 mục 5): mọi thay đổi API phải hiện trong diff của PR.
"""

from __future__ import annotations

import argparse
import difflib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCHEMA_NAME = "openapi.yaml"


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


def _run(schema: Path, *, check: bool) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        # Sinh ra file tạm trước: lỗi giữa chừng không làm hỏng file đã commit
        generated = Path(tmp) / SCHEMA_NAME
        if _render(generated) != 0:
            print("ERROR: drf-spectacular failed to generate a valid schema", file=sys.stderr)
            return 1
        expected = generated.read_text(encoding="utf-8")
    try:
        current = schema.read_text(encoding="utf-8") if schema.exists() else ""
    except UnicodeDecodeError as exc:
        raise GeneratorError(f"{schema}: {exc}") from exc
    if current == expected:
        return 0
    if check:
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=schema.name,
            tofile="manage.py spectacular",
        )
        sys.stdout.writelines(diff)
        print(f"{schema.name} is stale: run `make openapi` and commit the result")
        return 1
    schema.write_text(expected, encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    """Sinh lại `openapi.yaml`, hoặc chỉ báo lệch với `--check`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift, do not write")
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
