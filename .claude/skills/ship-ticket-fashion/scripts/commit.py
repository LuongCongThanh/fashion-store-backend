"""Commit một task của ticket: add đúng các file, gắn trailer Refs + Task, hook chạy trong log.

python .claude/skills/ship-ticket-fashion/scripts/commit.py <T> --task S1 \
    -m "feat(shared): add x" [--body "Vì sao …"] -- <file> [<file> …]
Task: plan | S<n> (slice trong state) | R1 | R2 | sync | close | ci (templates/commit-msg.md).
Hook pre-commit sửa file (ruff --fix, end-of-file) thì add lại và thử thêm một lần.
In `COMMIT <sha> [<task>] <subject> · <n> file`, hoặc `RED` kèm đoạn cuối log.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from check_ship import SUBJECT
from commit_map import TASK, read_commits
from common import git, load_state, resolve, state_dir, ticket_ref


def foreign_commits(commits: list[dict], ticket: str) -> str | None:
    """Commit trên nhánh mà `Refs:` không phải ticket này, ví dụ phiên khác commit nhầm vào."""
    others = [f"{c['sha']} {c['subject']}" for c in commits if c["refs"] != ticket]
    if not others:
        return None
    return (
        f"nhánh có commit không thuộc ticket: {'; '.join(others)}. "
        "Xem `git log origin/dev..HEAD`, đưa chúng ra khỏi nhánh rồi commit lại"
    )


def message(subject: str, body: str, ticket: str, task: str) -> str:
    parts = [subject, body.strip()] if body.strip() else [subject]
    return "\n\n".join([*parts, f"Refs: {ticket}\nTask: {task}"]) + "\n"


def check_task(task: str, state: dict) -> str | None:
    if not TASK.match(task):
        return f"task lạ: {task} (plan | S<n> | R1 | R2 | sync | close | ci)"
    slices = [s["id"] for s in state.get("slices", [])]
    if task.startswith("S") and task not in slices:
        return f"slice {task} không có trong state ({', '.join(slices) or 'chưa có slice'})"
    return None


def run(args: list[str], log: list[str]) -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env
    )
    log.append(f"$ git {' '.join(args)}\n{proc.stdout}{proc.stderr}")
    return proc.returncode


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--task", required=True)
    parser.add_argument("-m", "--subject", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num) or {}
    error = check_task(args.task, state)
    if error is None and not SUBJECT.match(args.subject):
        error = f"subject sai Conventional Commits: {args.subject}"
    if error is None:
        error = foreign_commits(read_commits(), ticket_ref(ticket))
    if error:
        print(f"TỪ CHỐI: {error}")
        return 1

    msg_file = state_dir() / "COMMIT_MSG"
    msg_file.write_text(
        message(args.subject, args.body, ticket_ref(ticket), args.task), encoding="utf-8"
    )
    log: list[str] = []
    paths = ["--", *args.paths]
    code = 1
    for _ in range(2):  # lần hai: hook đã sửa file, add lại rồi commit
        if run(["add", *paths], log) != 0:
            break
        # `-- <paths>` chỉ commit đúng các file này, kể cả khi index còn file khác đã stage
        code = run(["commit", "-F", str(msg_file), *paths], log)
        if code == 0:
            break

    log_path = state_dir() / "logs" / "commit.log"
    log_path.parent.mkdir(exist_ok=True)
    log_path.write_text("\n".join(log), encoding="utf-8")
    if code != 0:
        lines = [line for line in "\n".join(log).splitlines() if line.strip()]
        print(f"RED commit · log {log_path}")
        print("\n".join(lines[-30:]))
        return code
    files = len(git("show", "--format=", "--name-only", "HEAD").splitlines())
    print(
        f"COMMIT {git('rev-parse', '--short', 'HEAD')} [{args.task}] {args.subject} · {files} file"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
