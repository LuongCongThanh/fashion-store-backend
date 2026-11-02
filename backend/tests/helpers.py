"""Dựng project tạm cho test chạy script của backend bằng subprocess."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def isolated_env() -> dict[str, str]:
    """Biến môi trường của subprocess, bỏ cấu hình Django, coverage và pytest của phiên ngoài."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COVERAGE_", "COV_CORE_", "PYTEST_"))
        and key != "DJANGO_SETTINGS_MODULE"
    }
    env["PYTHONUTF8"] = "1"
    return env


def write_tree(root: Path, files: dict[str, str]) -> None:
    """Ghi `files` dưới `root` và thêm `__init__.py` cho mọi thư mục cha để thành package."""
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        for parent in path.parents:
            if parent == root:
                break
            (parent / "__init__.py").touch()


def importlinter_section() -> str:
    """Phần `[tool.importlinter]` thật của backend, để test kiểm đúng cấu hình đang commit."""
    lines = (BACKEND / "pyproject.toml").read_text(encoding="utf-8").splitlines(keepends=True)
    start = lines.index("[tool.importlinter]\n")
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("[") and "tool.importlinter" not in lines[index]
        ),
        len(lines),
    )
    return "".join(lines[start:end])
