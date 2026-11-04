"""Chạy một lệnh, ghi toàn bộ output vào log, chỉ in tóm tắt (xanh) hoặc đoạn cuối (đỏ).

python3 .claude/skills/ship-ticket-fashion/scripts/run_logged.py --label lint \
    --keep-going -- make lint
Log: .git/ship-ticket-fashion/logs/<label>.log

Máy không có `make` (Windows): `make <target>` chạy lần lượt các dòng lệnh của target trong
Makefile ở `--cwd` (sau các target tiên quyết), dừng ở dòng đỏ đầu tiên. `--keep-going` luôn
tách target thành từng dòng và chạy hết, nên một lần chạy in lỗi của mọi công cụ (ruff, mypy,
lint-imports…); recipe không tách được (biến make, dòng `-`) thì máy có `make` chạy nguyên
`make <target>`. Khi tách, tiến trình con nhận các biến `export` của Makefile như dưới `make`.
Tiến trình con luôn có `PYTHONIOENCODING=utf-8`.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from common import repo_root, state_dir


def logical_lines(makefile: str) -> list[str]:
    """Các dòng của Makefile sau khi nối dòng kết thúc bằng `\\`."""
    lines: list[str] = []
    pending = ""
    for line in makefile.splitlines():
        if pending:
            line = pending + " " + line.lstrip()
        if line.endswith("\\"):
            pending = line[:-1].rstrip()
            continue
        pending = ""
        lines.append(line)
    if pending:
        lines.append(pending)
    return lines


def make_rules(makefile: str) -> dict[str, tuple[list[str], list[str]]]:
    """target → (target tiên quyết, các dòng lệnh thô)."""
    rules: dict[str, tuple[list[str], list[str]]] = {}
    current: list[str] | None = None
    for line in logical_lines(makefile):
        if line.startswith("\t"):
            if current is not None and line.strip():
                current.append(line.strip())
            continue
        current = None
        head, sep, rest = line.partition(":")
        if not sep or rest.startswith("=") or head.startswith(("export ", "#", ".")):
            continue
        current = []
        rules[head.strip()] = (rest.split("#", 1)[0].split(), current)
    return rules


def make_recipe(makefile: str, target: str) -> list[list[str]]:
    """Các dòng lệnh của `target`, sau các dòng của target tiên quyết; bỏ tiền tố `@`/`+`."""
    rules = make_rules(makefile)
    if target not in rules:
        raise ValueError(f"Makefile không có target `{target}`")
    recipe: list[list[str]] = []
    done: set[str] = set()

    def visit(name: str) -> None:
        if name in done or name not in rules:
            return
        done.add(name)
        prerequisites, lines = rules[name]
        for prerequisite in prerequisites:
            visit(prerequisite)
        for line in lines:
            command = line.lstrip("@+")
            if command.startswith("-"):
                raise ValueError(f"target `{name}` có dòng bỏ qua lỗi (`-`); cần chạy qua make")
            recipe.append(shlex.split(command))

    visit(target)
    if any("$" in part for command in recipe for part in command):
        raise ValueError(f"target `{target}` dùng biến make; cần chạy qua make")
    return recipe


def make_exports(makefile: str) -> dict[str, str]:
    """Biến `export NAME := value` (hoặc `=`, `?=`) của Makefile, để chạy recipe như dưới make."""
    exports: dict[str, str] = {}
    for line in logical_lines(makefile):
        if not line.startswith("export "):
            continue
        name, sep, value = line[len("export ") :].partition("=")
        if sep:
            exports[name.rstrip(":?+ ").strip()] = value.split("#", 1)[0].strip()
    return exports


def expand(command: list[str], cwd: Path, *, keep_going: bool = False) -> list[list[str]]:
    has_make = shutil.which("make") is not None
    if command[0] != "make" or (has_make and not keep_going):
        return [command]
    if len(command) != 2:
        raise ValueError("chỉ tách được `make <target>`")
    try:
        return make_recipe((cwd / "Makefile").read_text(encoding="utf-8"), command[1])
    except ValueError:
        if has_make:
            return [command]
        raise


@dataclass(frozen=True)
class StepResult:
    command: list[str]
    code: int
    output: str


def run_steps(
    steps: list[list[str]], cwd: Path, env: dict[str, str], *, keep_going: bool
) -> list[StepResult]:
    """Kết quả từng bước đã chạy; không keep_going thì dừng ở bước đỏ."""
    results: list[StepResult] = []
    for step in steps:
        proc = subprocess.run(
            step,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results.append(StepResult(step, proc.returncode, proc.stdout + proc.stderr))
        if proc.returncode != 0 and not keep_going:
            break
    return results


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--cwd", default=".", help="thư mục chạy, tính từ gốc repo")
    parser.add_argument("--tail", type=int, default=40, help="số dòng cuối in ra khi lệnh đỏ")
    parser.add_argument(
        "--keep-going", action="store_true", help="chạy hết mọi dòng của target make, báo mọi bước đỏ"
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("thiếu lệnh sau --")

    cwd = repo_root() / Path(args.cwd)
    try:
        steps = expand(command, cwd, keep_going=args.keep_going)
    except ValueError as exc:
        parser.error(str(exc))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if steps != [command]:
        env.update(make_exports((cwd / "Makefile").read_text(encoding="utf-8")))

    logs = state_dir() / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / f"{args.label}.log"
    results = run_steps(steps, cwd, env, keep_going=args.keep_going)
    failed = [result for result in results if result.code != 0]
    returncode = failed[0].code if failed else 0
    transcript = [f"$ {' '.join(r.command)}\n{r.output}" for r in results]
    log.write_text("\n".join(transcript) + f"\nexit {returncode}\n", encoding="utf-8")

    if not failed:
        lines = [line for r in results for line in r.output.splitlines() if line.strip()]
        print(f"OK {args.label} · {lines[-1] if lines else '(không có output)'} · log {log}")
        return 0
    print(f"RED {args.label} (exit {returncode}, {len(failed)}/{len(results)} bước đỏ) · log {log}")
    tail = max(10, args.tail // len(failed))
    for result in failed:
        lines = [line for line in result.output.splitlines() if line.strip()]
        print(f"--- $ {' '.join(result.command)} (exit {result.code})")
        print("\n".join(lines[-tail:]))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
