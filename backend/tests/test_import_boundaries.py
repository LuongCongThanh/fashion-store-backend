"""Kiểm ranh giới module bằng cấu hình import-linter thật trên cây package tạm (12 mục 4, 8)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
GENERATOR = BACKEND / "scripts/gen_importlinter.py"
LINT_IMPORTS = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
# Cây tối thiểu: đủ module cho contract `layers`; inventory có phần nội bộ và public API,
# shared có outbox như repo thật
MODULES = (
    "identity",
    "catalog",
    "payments",
    "shipping",
    "inventory",
    "promotions",
    "ordering",
    "notifications",
)
TREE = {
    **{f"modules/{name}/__init__.py": "" for name in MODULES},
    "config/settings.py": "",
    "shared/events/publisher.py": "def publish(event):\n    return event\n",
    "shared/events/relay.py": "",
    "shared/events/tasks.py": "",
    "modules/inventory/models.py": "class StockItem:\n    pass\n",
    "modules/inventory/services/stock.py": "from modules.inventory.models import StockItem\n",
    "modules/inventory/selectors/stock.py": "from modules.inventory.models import StockItem\n",
    "modules/inventory/api/views.py": "from modules.inventory.services import stock\n",
    "modules/inventory/contracts.py": (
        "from modules.inventory.services.stock import StockItem\n\n\n"
        "def reserve_stock():\n    return StockItem()\n"
    ),
    "modules/inventory/tests/factories.py": "",
    "modules/ordering/services/__init__.py": "",
    "modules/ordering/tests/__init__.py": "",
}


def _isolated_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "DJANGO_SETTINGS_MODULE"}
    env["PYTHONUTF8"] = "1"
    return env


def _importlinter_section() -> str:
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


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        for parent in path.parents:
            if parent == root:
                break
            (parent / "__init__.py").touch()


def _lint(root: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Sinh contract cho cây tạm bằng generator thật rồi chạy lint-imports như `make lint`."""
    _write(root, {"pyproject.toml": _importlinter_section(), **TREE, **files})
    generated = subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GENERATOR), "--root", str(root)],
        cwd=root,
        env=_isolated_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    assert LINT_IMPORTS is not None
    return subprocess.run(  # noqa: S603 -- lint-imports của chính venv, chỉ đọc fixture do test tạo.
        [LINT_IMPORTS, "--config", str(root / "pyproject.toml"), "--no-cache"],
        cwd=root,
        env={**_isolated_env(), "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_ordering_services_calling_inventory_contracts_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"modules/ordering/services/checkout.py": "from modules.inventory import contracts\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ordering_tests_importing_inventory_models_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"modules/ordering/tests/test_checkout.py": "from modules.inventory import models\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "modules.ordering uses only the public API of modules.inventory BROKEN" in result.stdout


@pytest.mark.parametrize("internal", ["models", "services", "selectors", "api"])
def test_non_test_code_importing_other_module_internals_fails(
    tmp_path: Path, internal: str
) -> None:
    result = _lint(
        tmp_path,
        {"modules/ordering/services/checkout.py": f"import modules.inventory.{internal}\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "modules.ordering uses only the public API of modules.inventory BROKEN" in result.stdout


def test_module_importing_outbox_relay_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"modules/inventory/services/outbox.py": "from shared.events import relay\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Modules publish events only via shared.events.publish BROKEN" in result.stdout
