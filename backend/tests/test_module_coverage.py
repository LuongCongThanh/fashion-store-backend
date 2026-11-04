"""Kiểm cổng coverage bằng dữ liệu thực trong project tạm, không mock coverage.py."""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from coverage import Coverage

from tests.helpers import BACKEND, isolated_env, write_tree

GATE = BACKEND / "scripts/check_module_coverage.py"
# Cùng cờ với `make test` và job backend của CI (12 mục 8)
PYTEST_COV = ["--cov=modules", "--cov=shared", "--cov-report="]
SERVICE = "def choose(flag):\n    if flag:\n        return 1\n    return 2\n"


def _choices(count: int) -> str:
    cases = "".join(
        f"    if value == {number}:\n        return {number}\n" for number in range(count)
    )
    return "def choose(value):\n" + cases + "    return -1\n"


def _write(root: Path, files: dict[str, str]) -> None:
    write_tree(root, {"modules/__init__.py": "", "shared/__init__.py": "", **files})


def _measure(
    root: Path,
    files: dict[str, str],
    exercise: str,
    *,
    branch: bool = True,
    data_file: str = ".coverage",
) -> Path:
    _write(root, files)
    (root / "exercise.py").write_text(exercise, encoding="utf-8")
    path = root / data_file
    command = [sys.executable, "-m", "coverage", "run", "--source=modules,shared"]
    if branch:
        command.append("--branch")
    result = subprocess.run(  # noqa: S603 -- Python cố định, chỉ chạy fixture do test tạo.
        [*command, "exercise.py"],
        cwd=root,
        env={**isolated_env(), "COVERAGE_FILE": str(path)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return path


def _collect(root: Path, data_file: str, *options: str) -> subprocess.CompletedProcess[str]:
    """Chạy pytest với pytest-cov và cấu hình coverage của backend, như `make test`."""
    result = subprocess.run(  # noqa: S603 -- Python cố định, chỉ chạy test do fixture tạo.
        [
            sys.executable,
            "-m",
            "pytest",
            *options,
            *PYTEST_COV,
            f"--cov-config={BACKEND / 'pyproject.toml'}",
            "-p",
            "no:cacheprovider",
        ],
        cwd=root,
        env={
            **isolated_env(),
            "COVERAGE_FILE": str(root / data_file),
            "PYTEST_XDIST_AUTO_NUM_WORKERS": "2",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _gate(
    root: Path,
    data_file: str | None = None,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Chạy cổng như CI; không truyền `data_file` thì cổng tự lấy theo cấu hình coverage."""
    options = [] if data_file is None else ["--data-file", data_file]
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GATE), "--root", str(root), *options],
        cwd=cwd or root,
        env={**isolated_env(), **(env or {})},
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


def test_gate_ignores_django_app_packages(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {
            "modules/catalog/__init__.py": "",
            "modules/management/commands/purge.py": "",
            "modules/migrations/0001_initial.py": "",
            "modules/templates/email.txt": "",
        },
        "import modules.catalog\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "catalog: SKIP (no services/ or handlers.py)\n"


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
            "shared/idempotency/http.py": SERVICE,
            "shared/idempotency/__init__.py": SERVICE,
            "shared/tasks.py": SERVICE,
        },
        "from shared.events.relay import choose as relay\n"
        "from shared.idempotency.http import choose as idempotency\n"
        "from shared.idempotency import choose as claim\n"
        "from shared.tasks import choose as task\n"
        "relay(True)\nidempotency(True)\nclaim(True)\ntask(True)\n",
    )

    result = _gate(tmp_path)

    assert result.returncode == 1
    assert "shared: 4/8 branches (50.00%) FAIL" in result.stdout


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


def test_gate_reads_data_file_from_coverage_environment(tmp_path: Path) -> None:
    files = {"modules/catalog/services/product.py": SERVICE}
    _measure(
        tmp_path,
        files,
        "from modules.catalog.services.product import choose\nchoose(True)\nchoose(False)\n",
    )
    fresh = _measure(
        tmp_path,
        files,
        "from modules.catalog.services.product import choose\nchoose(True)\n",
        data_file="fresh.coverage",
    )

    result = _gate(tmp_path, env={"COVERAGE_FILE": str(fresh)})

    assert result.returncode == 1
    assert "catalog: 1/2 branches (50.00%) FAIL" in result.stdout


def test_gate_applies_project_coverage_config(tmp_path: Path) -> None:
    _measure(
        tmp_path,
        {
            "pyproject.toml": '[tool.coverage.run]\ndata_file = "branch.coverage"\n\n'
            '[tool.coverage.report]\nexclude_also = ["if flag:"]\n',
            "modules/catalog/services/product.py": SERVICE,
        },
        "from modules.catalog.services.product import choose\nchoose(False)\n",
        data_file="branch.coverage",
    )

    result = _gate(tmp_path)

    assert result.returncode == 0
    assert "catalog: 0/0 branches (no branches) PASS" in result.stdout


def test_gate_resolves_data_file_option_from_working_directory(tmp_path: Path) -> None:
    root = tmp_path / "backend"
    _measure(
        root,
        {"modules/catalog/services/product.py": SERVICE},
        "from modules.catalog.services.product import choose\nchoose(True)\n",
    )

    result = _gate(root, "backend/.coverage", cwd=tmp_path)

    assert result.returncode == 1
    assert "catalog: 1/2 branches (50.00%) FAIL" in result.stdout


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


def test_parallel_collection_matches_serial_branch_counts(tmp_path: Path) -> None:
    def tests(name: str, values: range) -> str:
        cases = "".join(
            f"def test_{index}():\n    {name}({number})\n\n" for index, number in enumerate(values)
        )
        return f"from modules.{name}.services.{name} import choose as {name}\n\n" + cases

    _write(
        tmp_path,
        {
            "pytest.ini": "[pytest]\npythonpath = .\n",
            "modules/catalog/services/catalog.py": _choices(5),
            "modules/inventory/services/inventory.py": _choices(5),
            "tests/test_catalog_low.py": tests("catalog", range(-1, 2)),
            "tests/test_catalog_high.py": tests("catalog", range(2, 5)),
            "tests/test_inventory.py": tests("inventory", range(-1, 1)),
        },
    )

    serial = _collect(tmp_path, "serial.coverage")
    parallel = _collect(tmp_path, "parallel.coverage", "-n", "auto")
    serial_gate = _gate(tmp_path, "serial.coverage")
    parallel_gate = _gate(tmp_path, "parallel.coverage")

    assert "8 passed" in serial.stdout
    assert "2 workers [8 items]" in parallel.stdout
    assert parallel_gate.returncode == serial_gate.returncode == 1
    assert parallel_gate.stdout == serial_gate.stdout
    assert "catalog: 10/10 branches (100.00%) PASS" in parallel_gate.stdout
    assert "inventory: 6/10 branches (60.00%) FAIL" in parallel_gate.stdout
