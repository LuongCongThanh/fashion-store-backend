"""Kiểm ranh giới module bằng cấu hình import-linter thật trên cây package tạm (12 mục 4, 8)."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.tooling.helpers import ROOT, importlinter_section, isolated_env, write_tree

GENERATOR = ROOT / "scripts/gen_importlinter.py"
LINT_IMPORTS = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
# Cây tối thiểu: đủ module cho contract `layers`; inventory có phần nội bộ và public API,
# common có outbox và chuỗi import gián tiếp tới relay (common.tasks → operations → relay → tasks)
MODULES = (
    "geo",
    "identity",
    "catalog",
    "payments",
    "shipping",
    "inventory",
    "promotions",
    "ordering",
    "notifications",
)
# `pyproject.toml` chỉ khai lớp của module đã có code; cây tạm dùng đủ thứ tự lớp ở 02 mục 3
# để kiểm contract `layers` với cả module tương lai
PLANNED_LAYERS = """layers = [
    "apps.notifications",
    "apps.ordering",
    "apps.inventory | apps.promotions",
    "apps.identity | apps.catalog | apps.payments | apps.shipping",
    "apps.geo",
    "common",
]"""
TREE = {
    **{f"apps/{name}/__init__.py": "" for name in MODULES},
    "config/settings.py": "",
    "common/events/publisher.py": "def publish(event):\n    return event\n",
    "common/events/tasks.py": "def dispatch_event():\n    pass\n",
    "common/events/relay.py": "from common.events.tasks import dispatch_event\n",
    "common/events/operations.py": "from common.events.relay import dispatch_event\n",
    "common/tasks.py": (
        "from common.events import operations\n\n\n"
        "def enqueue_on_commit(task_name):\n    return operations, task_name\n"
    ),
    "apps/inventory/models.py": "class StockItem:\n    pass\n",
    "apps/inventory/services/stock.py": "from apps.inventory.models import StockItem\n",
    "apps/inventory/selectors/stock.py": "from apps.inventory.models import StockItem\n",
    "apps/inventory/api/views.py": "from apps.inventory.services import stock\n",
    "apps/inventory/contracts.py": (
        "from apps.inventory.services.stock import StockItem\n\n\n"
        "def reserve_stock():\n    return StockItem()\n"
    ),
    "apps/inventory/tests/factories.py": "",
    "apps/ordering/services/__init__.py": "",
    "apps/ordering/tests/__init__.py": "",
}


def _lint(root: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Sinh contract cho cây tạm bằng generator thật rồi chạy lint-imports như `make lint`."""
    section = re.sub(
        r"layers = \[\n.*?\n\]", PLANNED_LAYERS, importlinter_section(), count=1, flags=re.S
    )
    write_tree(root, {"pyproject.toml": section, **TREE, **files})
    generated = subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GENERATOR)],
        cwd=root,
        env=isolated_env(),
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
        env={**isolated_env(), "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_ordering_services_calling_inventory_contracts_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"apps/ordering/services/checkout.py": "from apps.inventory import contracts\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ordering_tests_importing_inventory_models_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"apps/ordering/tests/test_checkout.py": "from apps.inventory import models\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "apps.ordering uses only the public API of apps.inventory BROKEN" in result.stdout


@pytest.mark.parametrize("internal", ["models", "services", "selectors", "api"])
def test_non_test_code_importing_other_module_internals_fails(
    tmp_path: Path, internal: str
) -> None:
    result = _lint(
        tmp_path,
        {"apps/ordering/services/checkout.py": f"import apps.inventory.{internal}\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "apps.ordering uses only the public API of apps.inventory BROKEN" in result.stdout


def test_module_importing_outbox_relay_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"apps/inventory/services/outbox.py": "from common.events import relay\n"},
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Modules publish events only via common.events.publish BROKEN" in result.stdout


def test_module_enqueueing_task_via_shared_tasks_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"apps/inventory/services/stock.py": "from common.tasks import enqueue_on_commit\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ordering_services_importing_inventory_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "apps/ordering/services/checkout.py": ("from apps.inventory.tests import factories\n"),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Only tests of other modules import apps.inventory.tests BROKEN" in result.stdout


def test_inventory_tests_importing_ordering_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "apps/ordering/tests/factories.py": "",
            "apps/inventory/tests/test_stock.py": ("from apps.ordering.tests import factories\n"),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Layer order between modules BROKEN" in result.stdout


def test_payments_tests_importing_shipping_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "apps/shipping/tests/factories.py": "",
            "apps/payments/tests/test_refund.py": ("from apps.shipping.tests import factories\n"),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Layer order between modules BROKEN" in result.stdout


def test_ordering_tests_importing_inventory_factories_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"apps/ordering/tests/test_cart.py": "from apps.inventory.tests import factories\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
