"""Kiểm tra marker pytest (--strict-markers, concurrency, flow, br) và lệnh br-report (12 mục 3)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.tooling.helpers import ROOT, isolated_env, write_tree

BR_REPORT_SCRIPT = ROOT / "scripts/br_report.py"


def _run_pytest(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = isolated_env()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(  # noqa: S603 -- Python và pytest cố định, chạy fixture do test tạo.
        [sys.executable, "-m", "pytest", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _run_br_report(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = isolated_env()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(  # noqa: S603 -- Python và script cố định, chạy fixture do test tạo.
        [sys.executable, str(BR_REPORT_SCRIPT), *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_strict_markers_rejects_undeclared(tmp_path: Path) -> None:
    """AC1: Test dùng marker chưa khai báo thì pytest báo lỗi do --strict-markers."""
    # Chạy trên project hiện tại với marker không tồn tại
    result = _run_pytest(
        ROOT,
        "-c",
        str(ROOT / "pyproject.toml"),
        "-m",
        "non_existent_marker_12345",
        "--collect-only",
    )
    # Pytest với --strict-markers thoát mã 4 khi dùng marker chưa khai báo trong -m
    assert result.returncode == 4
    output = result.stdout + result.stderr
    assert "not a registered marker" in output or "Unknown" in output

    # Kiểm tra trong test function giả lập
    write_tree(
        tmp_path,
        {
            "pyproject.toml": (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            "test_sample.py": (
                "import pytest\n@pytest.mark.undeclared_marker\ndef test_sample():\n    pass\n"
            ),
        },
    )
    test_result = _run_pytest(tmp_path, "test_sample.py", "--collect-only")
    assert test_result.returncode in (2, 4)
    test_output = test_result.stdout + test_result.stderr
    assert "undeclared_marker" in test_output

    # Các marker đã khai báo (br, concurrency, flow) được chấp nhận mà không báo lỗi
    valid_test = (
        "import pytest\n"
        "@pytest.mark.br('BR-CAT-01')\n"
        "@pytest.mark.concurrency\n"
        "@pytest.mark.flow\n"
        "def test_valid():\n"
        "    pass\n"
    )
    (tmp_path / "test_valid.py").write_text(valid_test, encoding="utf-8")
    valid_result = _run_pytest(tmp_path, "test_valid.py", "--collect-only")
    assert valid_result.returncode == 0


def test_marker_filtering_concurrency_and_flow(tmp_path: Path) -> None:
    """AC2: pytest -m concurrency và pytest -m flow chỉ chạy đúng nhóm test đó."""
    write_tree(
        tmp_path,
        {
            "pyproject.toml": (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            "test_sample.py": (
                "import pytest\n"
                "@pytest.mark.concurrency\n"
                "def test_concurrent():\n"
                "    assert True\n\n"
                "@pytest.mark.flow\n"
                "def test_flowing():\n"
                "    assert True\n\n"
                "def test_plain():\n"
                "    assert True\n"
            ),
        },
    )

    concurrency_run = _run_pytest(tmp_path, "-m", "concurrency", "test_sample.py", "-q")
    assert concurrency_run.returncode == 0
    assert "1 passed" in concurrency_run.stdout
    assert "2 deselected" in concurrency_run.stdout

    flow_run = _run_pytest(tmp_path, "-m", "flow", "test_sample.py", "-q")
    assert flow_run.returncode == 0
    assert "1 passed" in flow_run.stdout
    assert "2 deselected" in flow_run.stdout


def test_br_report_outputs_untested_codes_and_exits_zero(tmp_path: Path) -> None:
    """AC3: make br-report in đúng danh sách mã BR-xxx chưa có test và luôn thoát với mã 0."""
    # 1. Chạy trên project thật: thoát 0 và in ra các mã BR-xxx
    real_run = _run_br_report(ROOT)
    assert real_run.returncode == 0
    lines = [line.strip() for line in real_run.stdout.splitlines() if line.strip()]
    assert len(lines) > 0
    assert all(line.startswith("BR-") for line in lines)
    # Chưa có test gắn marker br nào nên phải đủ 88 quy tắc
    assert len(lines) == 88
    assert lines[0] == "BR-CAT-01"

    # 2. Chạy trên thư mục tạm với test gắn @pytest.mark.br để kiểm tra lọc trừ
    dummy_rules = (
        "# Business Rules\n\n"
        "| Mã | Quy tắc |\n"
        "|---|---|\n"
        "| BR-CAT-01 | Rule 1 |\n"
        "| BR-CAT-02 | Rule 2 |\n"
        "| BR-CAT-03 | Rule 3 |\n"
    )
    rules_file = tmp_path / "rules.md"
    rules_file.write_text(dummy_rules, encoding="utf-8")

    write_tree(
        tmp_path,
        {
            "pyproject.toml": (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            "test_sample.py": (
                "import pytest\n"
                "@pytest.mark.br('BR-CAT-01', 'BR-CAT-03')\n"
                "def test_cats():\n"
                "    pass\n"
            ),
        },
    )

    filtered_run = _run_br_report(
        tmp_path,
        "--rules-file",
        str(rules_file),
        str(tmp_path / "test_sample.py"),
    )
    assert filtered_run.returncode == 0
    filtered_lines = [line.strip() for line in filtered_run.stdout.splitlines() if line.strip()]
    assert filtered_lines == ["BR-CAT-02"]
