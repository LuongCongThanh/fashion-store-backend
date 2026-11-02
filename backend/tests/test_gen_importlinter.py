"""Kiểm generator contract `forbidden` của import-linter trên cây package tạm (02 mục 8)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
GENERATOR = BACKEND / "scripts/gen_importlinter.py"


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


def _generate(root: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- Python và đường dẫn script cố định, không qua shell.
        [sys.executable, str(GENERATOR), "--root", str(root), *options],
        cwd=root,
        env=_isolated_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_check_reports_hand_edited_forbidden_contract(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": _importlinter_section(),
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
    _write(
        tmp_path,
        {"pyproject.toml": '[tool.importlinter]\nroot_packages = ["modules"]\n'},
    )

    result = _generate(tmp_path, "--check")

    assert result.returncode == 2
    assert "gen_importlinter" in result.stderr


def test_committed_pyproject_is_up_to_date() -> None:
    result = _generate(BACKEND, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
