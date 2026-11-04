"""Danh sách module nghiệp vụ trong `apps/`, dùng chung cho các script trong `scripts/`."""

from __future__ import annotations

from pathlib import Path

# Thư mục Django không phải module nghiệp vụ nếu lỡ nằm trong `apps/`
DJANGO_APP_DIRS = frozenset({"management", "migrations", "templates"})


def list_modules(root: Path) -> list[Path]:
    """Package con của `root/apps`, bỏ `_*`, thư mục của Django app và thư mục không phải
    package (vd. thư mục còn sót chỉ có `__pycache__`)."""
    modules = root / "apps"
    if not modules.is_dir():
        return []
    return [
        module
        for module in sorted(modules.iterdir())
        if (module / "__init__.py").is_file()
        and not module.name.startswith("_")
        and module.name not in DJANGO_APP_DIRS
    ]
