"""Bản đồ commit → task của nhánh: mỗi commit thuộc task nào, phase nào, AC nào.

python3 .claude/skills/ship-ticket-fashion/scripts/commit_map.py <T> [--md]
Đọc trailer `Task:` và `Refs:` của commit trong origin/dev..HEAD (templates/commit-msg.md).
--md: bảng markdown cho báo cáo, thân PR và thân commit squash.
"""

from __future__ import annotations

import argparse
import re
import sys

from common import git, load_state, resolve, ticket_ref

PHASE_OF = {"plan": "1 grill", "R": "4 review", "sync": "5 sync", "retro": "5 sync", "close": "6 ship", "ci": "6 ship"}
TASK = re.compile(r"^(plan|S\d+|R[12]|sync|retro|close|ci)$")
REPEATABLE = {"ci"}  # mỗi lần CI đỏ một commit; task khác đúng một commit


def phase_of(task: str) -> str:
    if task.startswith("S"):
        return "2 code"
    return PHASE_OF.get(task, PHASE_OF.get(task[:1], "?"))


def order_key(task: str) -> tuple[int, int]:
    rank = ["plan", "S", "R", "sync", "retro", "close", "ci"]
    head = task if task in rank else task[:1]
    num = int(task[1:]) if task[1:].isdigit() else 0
    return (rank.index(head) if head in rank else len(rank), num)


def read_commits() -> list[dict]:
    """Commit của nhánh, cũ → mới, bỏ commit merge (mất khi squash)."""
    trailer = "%(trailers:key={},valueonly,separator=%x2C)"
    fmt = "%x1e%h%x1f%s%x1f" + trailer.format("Task") + "%x1f" + trailer.format("Refs")
    log = ("log", "--no-merges", "--reverse", "--name-only", f"--format={fmt}")
    return parse_log(git(*log, "origin/dev..HEAD"))


def parse_log(raw: str) -> list[dict]:
    """Một lần `git log --name-only`: mỗi bản ghi bắt đầu bằng \\x1e, dòng đầu là các field,
    các dòng sau là file của commit."""
    commits = []
    for record in filter(None, (r.strip() for r in raw.split("\x1e"))):
        head, *files = record.splitlines()
        sha, subject, task, refs = [*head.split("\x1f"), "", "", ""][:4]
        commits.append(
            {
                "sha": sha,
                "subject": subject,
                "task": task.strip(),
                "refs": refs.strip(),
                "files": len([f for f in files if f]),
            }
        )
    return commits


def problems(commits: list[dict], ticket: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for c in commits:
        if not TASK.match(c["task"]):
            found.append(("FAIL", f"{c['sha']} thiếu trailer Task hợp lệ: {c['subject']}"))
        if c["refs"] != ticket:
            found.append(("FAIL", f"{c['sha']} Refs `{c['refs'] or '—'}` khác ticket `{ticket}`"))
        if not TASK.match(c["task"]):
            continue  # đã báo FAIL ở trên; task rỗng không phải task trùng
        if c["task"] in seen and c["task"] not in REPEATABLE:
            found.append(
                ("WARN", f"task {c['task']} có 2 commit ({seen[c['task']]}, {c['sha']}): gộp lại")
            )
        seen.setdefault(c["task"], c["sha"])
    return found


def acs_of(state: dict) -> dict[str, str]:
    return {s["id"]: ", ".join(str(a) for a in s.get("acs", [])) for s in state.get("slices", [])}


def render(commits: list[dict], state: dict, markdown: bool) -> str:
    acs = acs_of(state)
    rows = sorted(commits, key=lambda c: order_key(c["task"]))
    if markdown:
        lines = ["| Task | Phase | AC | Commit | File |", "| --- | --- | --- | --- | --- |"]
        lines += [
            f"| {c['task'] or '?'} | {phase_of(c['task'])} | {acs.get(c['task'], '—')} "
            f"| `{c['sha']}` {c['subject']} | {c['files']} |"
            for c in rows
        ]
        return "\n".join(lines)
    return "\n".join(
        f"{c['task'] or '?':<5} {phase_of(c['task']):<9} AC {acs.get(c['task'], '—'):<6} "
        f"{c['sha']} {c['subject']} ({c['files']} file)"
        for c in rows
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--md", action="store_true", help="in bảng markdown")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num) or {}
    ticket_path = ticket_ref(ticket)
    commits = read_commits()
    if not commits:
        print("Chưa có commit nào trên nhánh so với origin/dev")
        return 0
    print(render(commits, state, args.md))
    found = problems(commits, ticket_path)
    for level, message in found:
        print(f"{level} {message}")
    return 1 if any(level == "FAIL" for level, _ in found) else 0


if __name__ == "__main__":
    raise SystemExit(main())
