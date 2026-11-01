"""Kiểm branch coverage của từng module từ dữ liệu pytest-cov đã thu thập."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coverage import Coverage
from coverage.exceptions import CoverageException


def _groups(root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    modules = root / "modules"
    if modules.is_dir():
        for module in sorted(modules.iterdir()):
            if not module.is_dir() or module.name.startswith("_"):
                continue
            files = sorted((module / "services").rglob("*.py"))
            handler = module / "handlers.py"
            if handler.is_file():
                files.append(handler)
            groups[module.name] = files
    shared = root / "shared"
    files = [
        path
        for path in sorted((shared / "events").rglob("*.py"))
        if "tests" not in path.relative_to(shared / "events").parts
    ]
    files.extend(
        path for path in (shared / "api/idempotency.py", shared / "tasks.py") if path.is_file()
    )
    if files:
        groups["shared"] = files
    return groups


def _check(root: Path, data_file: Path) -> int:
    if not data_file.is_file():
        raise CoverageException(f"coverage data file is missing: {data_file}")
    coverage = Coverage(data_file=str(data_file), config_file=False)
    coverage.load()
    if not coverage.get_data().has_arcs():
        raise CoverageException("branch coverage data is required")
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
    parser.add_argument("--data-file", type=Path, default=Path(".coverage"))
    args = parser.parse_args()
    try:
        return _check(args.root.resolve(), args.root.resolve() / args.data_file)
    except (CoverageException, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
