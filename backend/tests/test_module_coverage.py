"""Kiểm cổng coverage bằng dữ liệu thực trong project tạm, không mock coverage.py."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

from coverage import Coverage

GATE = Path(__file__).resolve().parents[1] / "scripts/check_module_coverage.py"
SERVICE = "def choose(flag):\n    if flag:\n        return 1\n    return 2\n"


def _choices(count: int) -> str:
    cases = "".join(
        f"    if value == {number}:\n        return {number}\n" for number in range(count)
    )
    return "def choose(value):\n" + cases + "    return -1\n"


def _isolated_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COVERAGE_", "COV_CORE_"))
        and key not in {"PYTEST_ADDOPTS", "PYTEST_PLUGINS", "DJANGO_SETTINGS_MODULE"}
    }
    env["PYTHONUTF8"] = "1"
    return env


def _measure(root: Path, files: dict[str, str], exercise: str, *, branch: bool = True) -> Path:
    for relative, text in {"modules/__init__.py": "", "shared/__init__.py": "", **files}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        for parent in path.parents:
            if parent == root:
                break
            (parent / "__init__.py").touch()
    (root / "exercise.py").write_text(exercise, encoding="utf-8")
    data_file = root / ".coverage"
    command = [sys.executable, "-m", "coverage", "run", "--source=modules,shared"]
    if branch:
        command.append("--branch")
    result = subprocess.run(  # noqa: S603 -- Python cố định, chỉ chạy fixture do test tạo.
        [*command, "exercise.py"],
        cwd=root,
        env={**_isolated_env(), "COVERAGE_FILE": str(data_file)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return data_file


def _gate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GATE), "--root", str(root)],
        cwd=root,
        env=_isolated_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_gate_rejects_low_branches_despite_high_combined_coverage(tmp_path: Path) -> None:
    source = SERVICE + "\n".join(f"value_{number} = {number}" for number in range(30)) + "\n"
    data_file = _measure(
        tmp_path,
        {"modules/catalog/services/product.py": source},
        "from modules.catalog.services.product import choose\nchoose(True)\n",
    )
    coverage = Coverage(data_file=str(data_file), config_file=False)
    coverage.load()
    combined = coverage.report(file=io.StringIO())

    result = _gate(tmp_path)

    assert combined > 80
    assert result.returncode == 1
    assert "catalog: 1/2 branches (50.00%) FAIL" in result.stdout


def test_gate_checks_modules_independently(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {
            "modules/catalog/services/product.py": _choices(5),
            "modules/inventory/services/stock.py": _choices(5),
        },
        "from modules.catalog.services.product import choose as product\n"
        "from modules.inventory.services.stock import choose as stock\n"
        "for value in range(-1, 5):\n    product(value)\nstock(-1)\nstock(0)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "catalog: 10/10 branches (100.00%) PASS" in result.stdout
    assert "inventory: 6/10 branches (60.00%) FAIL" in result.stdout


def test_gate_skips_empty_modules(tmp_path: Path) -> None:
    _measure(tmp_path, {"modules/catalog/__init__.py": ""}, "import modules.catalog\n")

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "catalog: SKIP (no services/ or handlers.py)" in result.stdout


def test_gate_checks_handlers_without_services(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/handlers.py": SERVICE},
        "from modules.catalog.handlers import choose\nchoose(True)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "catalog: 1/2 branches (50.00%) FAIL" in result.stdout


def test_gate_counts_unexecuted_service_files(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/services/product.py": SERVICE},
        "import modules.catalog\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "catalog: 0/2 branches (0.00%) FAIL" in result.stdout


def test_gate_checks_shared_targets(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {
            "shared/events/relay.py": SERVICE,
            "shared/api/idempotency.py": SERVICE,
            "shared/tasks.py": SERVICE,
        },
        "from shared.events.relay import choose as relay\n"
        "from shared.api.idempotency import choose as idempotency\n"
        "from shared.tasks import choose as task\n"
        "relay(True)\nidempotency(True)\ntask(True)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "shared: 3/6 branches (50.00%) FAIL" in result.stdout


def test_gate_ignores_unrelated_low_coverage(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {
            "modules/catalog/services/product.py": SERVICE,
            "modules/catalog/selectors/products.py": SERVICE,
            "shared/geo/selectors.py": SERVICE,
        },
        "from modules.catalog.services.product import choose\nchoose(True)\nchoose(False)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "catalog: 2/2 branches (100.00%) PASS" in result.stdout


def test_gate_rejects_statement_only_data(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/services/product.py": SERVICE},
        "from modules.catalog.services.product import choose\nchoose(True)\n",
        branch=False,
    )

    result = _gate(tmp_path)

    assert result.returncode == 2
    assert "branch coverage data is required" in result.stderr


def test_gate_rejects_missing_data(tmp_path: Path) -> None:
    result = _gate(tmp_path)

    assert result.returncode == 2
    assert "coverage data file is missing" in result.stderr


def test_gate_reports_targets_without_branches(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/services/product.py": "def price():\n    return 100\n"},
        "from modules.catalog.services.product import price\nprice()\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "catalog: 0/0 branches (no branches) PASS" in result.stdout


def test_gate_excludes_shared_event_tests_from_branch_totals(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"shared/events/relay.py": SERVICE, "shared/events/tests/test_relay.py": SERVICE},
        "from shared.events.relay import choose\nchoose(True)\nchoose(False)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "shared: 2/2 branches (100.00%) PASS" in result.stdout


def test_gate_rejects_branch_percentage_that_rounds_up_to_eighty(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/services/product.py": _choices(201)},
        "from modules.catalog.services.product import choose\n"
        "for value in range(119):\n    choose(value)\nchoose(-1)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "catalog: 320/402 branches (79.60%) FAIL" in result.stdout


def test_gate_accepts_exactly_eighty_percent(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {"modules/catalog/services/product.py": _choices(5)},
        "from modules.catalog.services.product import choose\n"
        "for value in range(-1, 3):\n    choose(value)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "catalog: 8/10 branches (80.00%) PASS" in result.stdout
