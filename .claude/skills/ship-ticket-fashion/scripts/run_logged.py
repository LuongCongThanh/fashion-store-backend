"""Chạy một lệnh, ghi toàn bộ output vào log, chỉ in tóm tắt (xanh) hoặc đoạn cuối (đỏ).

python3 .claude/skills/ship-ticket-fashion/scripts/run_logged.py --label lint --cwd backend \
    --keep-going -- make lint
Log: .git/ship-ticket-fashion/logs/<label>.log

Máy không có `make` (Windows): `make <target>` chạy lần lượt các dòng lệnh của target trong
Makefile ở `--cwd`, dừng ở dòng đỏ đầu tiên. `--keep-going` luôn tách target thành từng dòng
và chạy hết, nên một lần chạy in lỗi của mọi công cụ (ruff, mypy, lint-imports…). Tiến trình
con luôn có `PYTHONIOENCODING=utf-8`.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from common import repo_root, state_dir


def make_recipe(makefile: str, target: str) -> list[list[str]]:
    """Các dòng lệnh của `target` (dòng thụt tab ngay sau `target:`)."""
    recipe: list[list[str]] = []
    inside = False
    for line in makefile.splitlines():
        if line.startswith("\t"):
            if inside and line.strip():
                recipe.append(shlex.split(line.strip()))
            continue
        inside = line.split(":", 1)[0].strip() == target and ":" in line
        if recipe and not inside:
            break
    if not recipe:
        raise ValueError(f"Makefile không có target `{target}`")
    if any("$" in part for command in recipe for part in command):
        raise ValueError(f"target `{target}` dùng biến make; cần cài make")
    return recipe


def expand(command: list[str], cwd: Path, *, keep_going: bool = False) -> list[list[str]]:
    if command[0] != "make" or (shutil.which("make") and not keep_going):
        return [command]
    if len(command) != 2:
        raise ValueError("chỉ tách được `make <target>`")
    return make_recipe((cwd / "Makefile").read_text(encoding="utf-8"), command[1])


def run_steps(
    steps: list[list[str]], cwd: Path, env: dict[str, str], *, keep_going: bool
) -> list[tuple[list[str], int, str]]:
    """(lệnh, exit code, output) của từng bước đã chạy; không keep_going thì dừng ở bước đỏ."""
    results: list[tuple[list[str], int, str]] = []
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
        results.append((step, proc.returncode, proc.stdout + proc.stderr))
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

    logs = state_dir() / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / f"{args.label}.log"
    results = run_steps(steps, cwd, env, keep_going=args.keep_going)
    failed = [(step, code, out) for step, code, out in results if code != 0]
    returncode = failed[0][1] if failed else 0
    transcript = [f"$ {' '.join(step)}\n{out}" for step, _, out in results]
    log.write_text("\n".join(transcript) + f"\nexit {returncode}\n", encoding="utf-8")

    if not failed:
        lines = [line for _, _, out in results for line in out.splitlines() if line.strip()]
        print(f"OK {args.label} · {lines[-1] if lines else '(không có output)'} · log {log}")
        return 0
    print(f"RED {args.label} (exit {returncode}, {len(failed)}/{len(results)} bước đỏ) · log {log}")
    tail = max(10, args.tail // len(failed))
    for step, code, out in failed:
        lines = [line for line in out.splitlines() if line.strip()]
        print(f"--- $ {' '.join(step)} (exit {code})")
        print("\n".join(lines[-tail:]))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
