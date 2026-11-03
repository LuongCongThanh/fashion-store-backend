"""Đóng ticket trong PR của nó: Status resolved, dòng **PR:**, tick acceptance criteria.

Theo docs/agents/issue-tracker.md mục "Đóng ticket".
python3 .claude/skills/ship-ticket-fashion/scripts/close_ticket.py <T> --pr 23
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import cast

from check_ac_trace import trace
from common import load_state, repo_root, resolve
from progress import REPORT, SPEC, find_section
from state import validate


def fill_pr(text: str, pr: int) -> str:
    """Báo cáo (phase 3) có "**PR:** chưa mở": thay bằng số PR."""
    return re.sub(r"(\*\*PR:\*\*) (?!#\d)[^·\n]*?(?=\s*·|\s*$)", rf"\1 #{pr}", text, flags=re.M)


def close(
    text: str, pr: int, untestable: set[int] = frozenset()
) -> tuple[str, list[str], list[str]]:
    """`spec.md` → (text mới, AC vừa tick, AC bỏ qua vì nằm trong untestable)."""
    if not re.search(r"^Status:", text, re.M):
        raise SystemExit("Ticket không có dòng Status:")
    # chỉ dòng **PR:** #<số> đứng riêng mới tính là đã có dòng PR của ticket
    text = fill_pr(text, pr)
    status_line = "Status: resolved"
    if not re.search(r"^\*\*PR:\*\* #\d+\s*$", text, re.M):
        status_line += f"\n\n**PR:** #{pr}"
    text = re.sub(r"^Status:.*$", status_line, text, count=1, flags=re.M)

    match = find_section(text, "Acceptance criteria")
    if not match:
        return text, [], []
    ticked, skipped, lines = [], [], []
    num = 0  # AC đếm từ 1 theo thứ tự checkbox, như state.untestable
    for line in match.group(1).split("\n"):
        item = re.match(r"^(\s*)- \[([ xX])\] (.+)$", line)
        if item:
            num += 1
            if item.group(2) == " " and num in untestable:
                skipped.append(item.group(3))
            elif item.group(2) == " ":
                ticked.append(item.group(3))
                line = f"{item.group(1)}- [x] {item.group(3)}"
        lines.append(line)
    return text[: match.start(1)] + "\n".join(lines) + text[match.end(1) :], ticked, skipped


def close_blockers(state: dict | None, pr: int, ac_total: int, backend: Path) -> list[str]:
    """Điều kiện fail-closed trước khi ghi trạng thái resolved và tick AC."""
    if state is None:
        return ["không có state; không thể chứng minh AC đã hoàn tất"]
    blockers = []
    blockers.extend(validate(state, ac_total))
    if state.get("phase") != "ship":
        blockers.append(f"phase là {state.get('phase')}, cần phase ship")
    if not state.get("gates", {}).get("g2"):
        blockers.append("G2 chưa được duyệt")
    if state.get("pr") != pr:
        blockers.append(f"PR #{pr} khác PR trong state ({state.get('pr') or '—'})")
    unfinished = [s.get("id", "?") for s in state.get("slices", []) if s.get("status") != "done"]
    if unfinished:
        blockers.append(f"slice chưa hoàn tất: {', '.join(unfinished)}")
    blockers.extend(trace(state, ac_total, backend, planned=False))
    return blockers


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--pr", type=int, required=True, help="số PR đóng ticket")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    blockers = close_blockers(state, args.pr, ticket.ac_total, repo_root() / "backend")
    if blockers:
        print("TỪ CHỐI: bằng chứng AC chưa đầy đủ")
        for blocker in blockers:
            print(f"  - {blocker}")
        return 1
    state = cast(dict, state)
    untestable = {int(k) for k in state.get("untestable", {})}

    spec = ticket.path / SPEC
    new_text, ticked, skipped = close(spec.read_text(encoding="utf-8"), args.pr, untestable)
    spec.write_text(new_text, encoding="utf-8", newline="\n")
    report = ticket.path / REPORT
    if report.exists():
        text = report.read_text(encoding="utf-8")
        report.write_text(fill_pr(text, args.pr), encoding="utf-8", newline="\n")

    print(f"{ticket.path.name}: Status resolved, PR #{args.pr}")
    if ticked:
        print("Đã tick (đối chiếu từng mục với báo cáo):")
        for item in ticked:
            print(f"  - {item}")
    if skipped:
        print("Chưa tick vì nằm trong untestable (đã kiểm tay thì tự tick):")
        for item in skipped:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
