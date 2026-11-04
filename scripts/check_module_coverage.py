"""Kiểm branch coverage của từng module từ dữ liệu pytest-cov đã thu thập."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _modules import list_modules
from coverage import Coverage
from coverage.exceptions import CoverageException


def _groups(root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for module in list_modules(root):
        files = sorted((module / "services").rglob("*.py"))
        handler = module / "handlers.py"
        if handler.is_file():
            files.append(handler)
        groups[module.name] = files
    common = root / "common"
    files = [
        path
        for package in ("events", "idempotency")
        for path in sorted((common / package).rglob("*.py"))
        if "tests" not in path.relative_to(common / package).parts
    ]
    if (common / "tasks.py").is_file():
        files.append(common / "tasks.py")
    if files:
        groups["common"] = files
    return groups


def _load(root: Path, data_file: Path | None) -> Coverage:
    # Nạp cấu hình coverage của project để áp exclude và partial_branches như `coverage report`
    config = root / "pyproject.toml"
    coverage = Coverage(config_file=str(config) if config.is_file() else False)
    if data_file is None:
        # COVERAGE_FILE, rồi `[tool.coverage.run] data_file`, rồi `.coverage`; tính từ root
        data_file = root / str(coverage.get_option("run:data_file"))
    if not data_file.is_file():
        raise CoverageException(f"coverage data file is missing: {data_file}")
    coverage.set_option("run:data_file", str(data_file))
    coverage.load()
    if not coverage.get_data().has_arcs():
        raise CoverageException("branch coverage data is required")
    return coverage


def _check(root: Path, data_file: Path | None) -> int:
    coverage = _load(root, data_file)
    failed = False
    for name, files in _groups(root).items():
        if not files:
            print(f"{name}: SKIP (no services/ or handlers.py)")
            continue
        total = covered = 0
        for path in files:
            for possible, taken in coverage.branch_stats(str(path)).values():
                total += possible
                covered += taken
        passed = covered * 100 >= total * 80
        percent = f"{covered * 100 / total:.2f}%" if total else "no branches"
        print(f"{name}: {covered}/{total} branches ({percent}) {'PASS' if passed else 'FAIL'}")
        failed |= not passed
    return int(failed)


def main() -> int:
    """Đọc đường dẫn dữ liệu và trả exit code của cổng coverage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--data-file", type=Path)
    args = parser.parse_args()
    try:
        data_file = args.data_file.resolve() if args.data_file else None
        return _check(args.root.resolve(), data_file)
    except (CoverageException, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
