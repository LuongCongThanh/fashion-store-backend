"""Chạy một lệnh, ghi toàn bộ output vào log, chỉ in tóm tắt (xanh) hoặc đoạn cuối (đỏ).

python3 .claude/skills/ship-ticket-fashion/scripts/run_logged.py --label test --cwd backend \
    -- make test
Log: .git/ship-ticket-fashion/logs/<label>.log

Máy không có `make` (Windows): `make <target>` chạy lần lượt các dòng lệnh của target trong
Makefile ở `--cwd`, dừng ở dòng đỏ đầu tiên. Tiến trình con luôn có `PYTHONIOENCODING=utf-8`.
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


def expand(command: list[str], cwd: Path) -> list[list[str]]:
    if command[0] != "make" or shutil.which("make"):
        return [command]
    if len(command) != 2:
        raise ValueError("không có make: chỉ hỗ trợ `make <target>`")
    return make_recipe((cwd / "Makefile").read_text(encoding="utf-8"), command[1])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--cwd", default=".", help="thư mục chạy, tính từ gốc repo")
    parser.add_argument("--tail", type=int, default=40, help="số dòng cuối in ra khi lệnh đỏ")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("thiếu lệnh sau --")

    cwd = repo_root() / Path(args.cwd)
    try:
        steps = expand(command, cwd)
    except ValueError as exc:
        parser.error(str(exc))
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    logs = state_dir() / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / f"{args.label}.log"
    output, returncode, transcript = "", 0, []
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
        output += proc.stdout + proc.stderr
        transcript.append(f"$ {' '.join(step)}\n{proc.stdout}{proc.stderr}")
        returncode = proc.returncode
        if returncode != 0:
            break
    log.write_text("\n".join(transcript) + f"\nexit {returncode}\n", encoding="utf-8")

    lines = [line for line in output.splitlines() if line.strip()]
    if returncode == 0:
        print(f"OK {args.label} · {lines[-1] if lines else '(không có output)'} · log {log}")
    else:
        print(f"RED {args.label} (exit {returncode}) · log {log}")
        print("\n".join(lines[-args.tail :]))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
