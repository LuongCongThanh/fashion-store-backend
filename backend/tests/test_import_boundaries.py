"""Kiểm ranh giới module bằng cấu hình import-linter thật trên cây package tạm (12 mục 4, 8)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import BACKEND, importlinter_section, isolated_env, write_tree

GENERATOR = BACKEND / "scripts/gen_importlinter.py"
LINT_IMPORTS = shutil.which("lint-imports", path=str(Path(sys.executable).parent))
# Cây tối thiểu: đủ module cho contract `layers`; inventory có phần nội bộ và public API,
# shared có outbox và chuỗi import gián tiếp tới relay (shared.tasks → operations → relay → tasks)
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
    "shared/events/tasks.py": "def dispatch_event():\n    pass\n",
    "shared/events/relay.py": "from shared.events.tasks import dispatch_event\n",
    "shared/events/operations.py": "from shared.events.relay import dispatch_event\n",
    "shared/tasks.py": (
        "from shared.events import operations\n\n\n"
        "def enqueue_on_commit(task_name):\n    return operations, task_name\n"
    ),
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


def _lint(root: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Sinh contract cho cây tạm bằng generator thật rồi chạy lint-imports như `make lint`."""
    write_tree(root, {"pyproject.toml": importlinter_section(), **TREE, **files})
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


def test_module_enqueueing_task_via_shared_tasks_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"modules/inventory/services/stock.py": "from shared.tasks import enqueue_on_commit\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_ordering_services_importing_inventory_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "modules/ordering/services/checkout.py": (
                "from modules.inventory.tests import factories\n"
            ),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Only tests of other modules import modules.inventory.tests BROKEN" in result.stdout


def test_inventory_tests_importing_ordering_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "modules/ordering/tests/factories.py": "",
            "modules/inventory/tests/test_stock.py": (
                "from modules.ordering.tests import factories\n"
            ),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Layer order between modules BROKEN" in result.stdout


def test_payments_tests_importing_shipping_factories_fails(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {
            "modules/shipping/tests/factories.py": "",
            "modules/payments/tests/test_refund.py": (
                "from modules.shipping.tests import factories\n"
            ),
        },
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Layer order between modules BROKEN" in result.stdout


def test_ordering_tests_importing_inventory_factories_passes(tmp_path: Path) -> None:
    result = _lint(
        tmp_path,
        {"modules/ordering/tests/test_cart.py": "from modules.inventory.tests import factories\n"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
