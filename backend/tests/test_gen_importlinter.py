"""Kiểm generator contract `forbidden` của import-linter trên cây package tạm (02 mục 8)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.helpers import BACKEND, importlinter_section, isolated_env, write_tree

GENERATOR = BACKEND / "scripts/gen_importlinter.py"


def _generate(root: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GENERATOR), *options],
        cwd=root,
        env=isolated_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_check_reports_hand_edited_forbidden_contract(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {
            "pyproject.toml": importlinter_section(),
            "modules/inventory/models.py": "",
            "modules/ordering/services/checkout.py": "",
        },
    )
    assert _generate(tmp_path).returncode == 0
    assert _generate(tmp_path, "--check").returncode == 0
    pyproject = tmp_path / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    edited = text.replace('    "modules.inventory.models",\n', "", 1)
    assert edited != text
    pyproject.write_text(edited, encoding="utf-8", newline="\n")

    result = _generate(tmp_path, "--check")

    assert result.returncode == 1
    assert '+    "modules.inventory.models",' in result.stdout


def test_check_rejects_missing_markers(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {"pyproject.toml": '[tool.importlinter]\nroot_packages = ["modules"]\n'},
    )

    result = _generate(tmp_path, "--check")

    assert result.returncode == 2
    assert "gen_importlinter" in result.stderr


def test_committed_pyproject_is_up_to_date() -> None:
    result = _generate(BACKEND, "--check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_check_rejects_invalid_toml(tmp_path: Path) -> None:
    write_tree(tmp_path, {"pyproject.toml": "[tool.importlinter\n"})

    result = _generate(tmp_path, "--check")

    assert result.returncode == 2
    assert result.stderr.startswith("ERROR: ")


def test_check_rejects_non_utf8_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_bytes(b"[tool.importlinter]\n# \xff\xfe\n")

    result = _generate(tmp_path, "--check")

    assert result.returncode == 2
    assert result.stderr.startswith("ERROR: ")
    assert "Traceback" not in result.stderr


def test_directory_without_init_is_not_a_module(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {
            "pyproject.toml": importlinter_section(),
            "modules/ordering/services/checkout.py": "",
        },
    )
    # Thư mục còn sót (chỉ còn file, không có __init__.py) không phải module nghiệp vụ
    stale = tmp_path / "modules/stale"
    stale.mkdir()
    (stale / "models.py").write_text("", encoding="utf-8")

    assert _generate(tmp_path).returncode == 0

    assert "modules.stale" not in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")


def test_target_without_internals_gets_no_pairwise_contract(tmp_path: Path) -> None:
    write_tree(
        tmp_path,
        {
            "pyproject.toml": importlinter_section(),
            "modules/inventory/__init__.py": "",
            "modules/ordering/services/checkout.py": "",
        },
    )

    assert _generate(tmp_path).returncode == 0

    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert "modules.inventory uses only the public API of modules.ordering" in text
    assert "public API of modules.inventory" not in text
