"""Sinh contract `forbidden` của import-linter giữa các module vào pyproject.toml (02 mục 8)."""

from __future__ import annotations

import argparse
import difflib
import sys
import tomllib
from pathlib import Path

from _modules import list_modules

BEGIN = "# BEGIN gen_importlinter"
END = "# END gen_importlinter"
# Phần public của module (02 mục 6.1)
PUBLIC_API = frozenset({"contracts", "events", "exceptions"})
# Test và factory của module: chiều import giữa test do contract `layers` kiểm, code ngoài test
# không được import (12 mục 4)
TESTS = "tests"
# Chỉ đẩy sự kiện qua shared.events.publish; relay và task của outbox là việc của shared (02 mục 8)
OUTBOX_INTERNALS = ("shared.events.relay", "shared.events.tasks")


class GeneratorError(Exception):
    """Lỗi đọc cấu hình hoặc thiếu dòng đánh dấu vùng sinh."""


def _children(module: Path) -> set[str]:
    """Package và module con thực sự tồn tại của module."""
    names = set()
    for child in module.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file():
            names.add(child.name)
        elif child.is_file() and child.suffix == ".py" and child.stem != "__init__":
            names.add(child.stem)
    return names


def _internals(module: Path) -> list[str]:
    """Phần nội bộ của module: mọi package và module con trừ public API và `tests`."""
    return sorted(_children(module) - PUBLIC_API - {TESTS})


def _contract(name: str, sources: list[str], forbidden: list[str], *, indirect: bool) -> str:
    def items(values: list[str]) -> str:
        return "".join(f'    "{value}",\n' for value in values)

    text = (
        "[[tool.importlinter.contracts]]\n"
        f'name = "{name}"\n'
        'type = "forbidden"\n'
        f"source_modules = [\n{items(sources)}]\n"
        f"forbidden_modules = [\n{items(forbidden)}]\n"
    )
    if indirect:
        text += "allow_indirect_imports = true\n"
    return text


def _tests_contracts(modules: list[Path]) -> list[str]:
    """Mỗi module có `tests` một contract: code ngoài `tests` của module khác không import nó.

    Factory chỉ dùng trong test (12 mục 4); test của module khác vẫn import được, theo chiều
    của contract `layers`.
    """
    contracts = []
    for target in modules:
        if TESTS not in _children(target):
            continue
        sources = [
            f"modules.{source.name}.{name}"
            for source in modules
            if source != target
            for name in sorted(_children(source) - {TESTS})
        ]
        if not sources:
            continue
        contracts.append(
            _contract(
                f"Only tests of other modules import modules.{target.name}.tests",
                sources,
                [f"modules.{target.name}.{TESTS}"],
                indirect=True,
            )
        )
    return contracts


def render(root: Path) -> str:
    """Toàn bộ vùng sinh, gồm cả hai dòng đánh dấu."""
    modules = list_modules(root)
    contracts = [
        _contract(
            "Modules publish events only via shared.events.publish",
            ["modules"],
            list(OUTBOX_INTERNALS),
            # Chỉ cấm import trực tiếp: test của module dùng shared.testing.events.drain_events,
            # hàm này gọi shared.events.relay
            indirect=True,
        )
    ]
    for target in modules:
        internals = _internals(target)
        if not internals:
            continue
        for source in modules:
            if source == target:
                continue
            contracts.append(
                _contract(
                    f"modules.{source.name} uses only the public API of modules.{target.name}",
                    [f"modules.{source.name}"],
                    [f"modules.{target.name}.{name}" for name in internals],
                    # Mặc định import-linter cấm cả chuỗi gián tiếp, mà lời gọi hợp lệ qua
                    # contracts luôn đi tiếp xuống phần nội bộ của module đích (02 mục 8)
                    indirect=True,
                )
            )
    contracts.extend(_tests_contracts(modules))
    header = (
        f"{BEGIN}\n"
        "# Sinh bởi scripts/gen_importlinter.py, không sửa tay: chạy lại script sau khi thêm\n"
        "# module hoặc phần nội bộ của module\n"
    )
    return header + "\n".join(contracts) + f"{END}\n"


def _split(text: str) -> tuple[str, str, str]:
    """Tách pyproject thành phần trước vùng sinh, vùng sinh và phần sau."""
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.rstrip("\n") == BEGIN]
    ends = [index for index, line in enumerate(lines) if line.rstrip("\n") == END]
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise GeneratorError(f"pyproject.toml needs exactly one '{BEGIN}' line before '{END}'")
    start, end = starts[0], ends[0] + 1
    return "".join(lines[:start]), "".join(lines[start:end]), "".join(lines[end:])


def _run(root: Path, *, check: bool) -> int:
    path = root / "pyproject.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise GeneratorError(f"{path}: {exc}") from exc
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise GeneratorError(f"{path}: {exc}") from exc
    before, current, after = _split(text)
    expected = render(root)
    if current == expected:
        return 0
    if check:
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile="pyproject.toml",
            tofile="gen_importlinter.py",
        )
        sys.stdout.writelines(diff)
        print("forbidden contracts are stale: run `uv run python scripts/gen_importlinter.py`")
        return 1
    path.write_text(before + expected + after, encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    """Sinh lại vùng contract `forbidden`, hoặc chỉ kiểm nó với `--check`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift, do not write")
    args = parser.parse_args()
    try:
        # Luôn chạy trên thư mục hiện tại (gốc repo ở Make và CI): không nhận đường dẫn từ CLI
        return _run(Path.cwd(), check=args.check)
    except (GeneratorError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
