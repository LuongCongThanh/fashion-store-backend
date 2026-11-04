"""Đóng ticket trong PR của nó: Status resolved, dòng **PR:**, tick acceptance criteria.

Theo docs/agents/issue-tracker.md mục "Đóng ticket". Cùng lúc ghi `docs/agents/ticket-history.md`
(thêm vào *Đã xong*, bỏ khỏi *Còn mở*) và thêm số ticket vào nhóm ✅ của dòng mốc trong bảng
*Tiến độ* của `.scratch/mvp-roadmap/map.md`; chỗ cần sửa tay in thành dòng `WARN`.
python3 .claude/skills/ship-ticket-fashion/scripts/close_ticket.py <T> --pr 23
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
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


def add_history(
    text: str, feature_path: str, folder: str, pr: int, day: str, title: str
) -> tuple[str, str | None]:
    """`ticket-history.md` → (text mới, ghi chú cần sửa tay hoặc None)."""
    marker = f"../../.scratch/{feature_path}/"
    sections = re.split(r"(?m)^(?=## )", text)
    index = next(
        (i for i, sec in enumerate(sections) if sec.startswith("## ") and marker in sec), None
    )
    if index is None:
        return text, f"ticket-history.md: không có mục của `{feature_path}`, thêm tay"
    link = f"[{folder[:2]}]({marker}issues/{folder}/spec.md)"
    lines, desc = [], title
    for line in sections[index].split("\n"):
        if line.startswith(f"- {link}"):
            parts = line.split(" · ")
            desc = parts[1] if len(parts) > 2 else desc
            continue
        lines.append(line)
    if any(re.match(rf"\d+\. {re.escape(link)}", line) for line in lines):
        return text, None
    if "### Đã xong" not in lines:
        return text, f"ticket-history.md: mục `{feature_path}` chưa có `### Đã xong`, thêm tay"
    start = lines.index("### Đã xong")
    last, count = start + 1, 0
    for j in range(start + 1, len(lines)):
        if lines[j].startswith(("### ", "## ")):
            break
        if item := re.match(r"(\d+)\. ", lines[j]):
            last, count = j, int(item.group(1))
    entry = f"{count + 1}. {link} · {desc} · PR #{pr} · {day}"
    lines[last + 1 : last + 1] = [entry] if count else [entry, ""]
    sections[index] = "\n".join(lines)
    return "".join(sections), None


def mark_progress(text: str, feature_path: str, num: int) -> tuple[str, list[str]]:
    """Thêm `NN` vào nhóm ✅ của dòng mốc trong bảng Tiến độ; báo nhóm khác còn nhắc NN."""
    nn = f"{num:02d}"
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Tiến độ"), None)
    if start is None:
        return text, ["map.md: không có mục `## Tiến độ`, sửa tay"]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    link = f"(../{feature_path}/spec.md)"
    row = next(
        (i for i in range(start, end) if lines[i].startswith("|") and link in lines[i]), None
    )
    if row is None:
        return text, [f"map.md: không có dòng Tiến độ của `{feature_path}`, sửa tay"]
    cells = lines[row].split("|")
    groups = cells[-2].strip().split(" · ")
    done = next((i for i, g in enumerate(groups) if g.startswith("✅")), None)
    if done is not None and re.search(rf"\b{nn}\b", groups[done]):
        return text, []
    if done is None:
        groups.insert(0, f"✅ {nn}")
        done = 0
    else:
        groups[done] = f"{groups[done]}, {nn}"
    notes = []
    for i, group in enumerate(groups):
        if i == done:
            continue
        ranges = re.findall(r"\b(\d{2})[\u2013-](\d{2})\b", group)
        in_range = any(int(a) <= num <= int(b) for a, b in ranges)
        if in_range or re.search(rf"(?<![\u2013-]){nn}(?![\u2013-])\b", group):
            notes.append(f"map.md: `{group}` vẫn nhắc ticket {nn}, sửa tay")
    cells[-2] = f" {' · '.join(groups)} "
    lines[row] = "|".join(cells)
    return "\n".join(lines), notes


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

    root = repo_root()
    feature_path = ticket.path.parent.parent.relative_to(root / ".scratch").as_posix()
    warnings = []
    history = root / "docs/agents/ticket-history.md"
    text, note = add_history(
        history.read_text(encoding="utf-8"),
        feature_path,
        ticket.path.name,
        args.pr,
        datetime.now(UTC).astimezone().strftime("%d/%m/%Y"),
        ticket.title,
    )
    history.write_text(text, encoding="utf-8", newline="\n")
    warnings += [note] if note else []
    roadmap = root / ".scratch/mvp-roadmap/map.md"
    text, notes = mark_progress(roadmap.read_text(encoding="utf-8"), feature_path, ticket.num)
    roadmap.write_text(text, encoding="utf-8", newline="\n")
    warnings += notes

    print(f"{ticket.path.name}: Status resolved, PR #{args.pr}; ticket-history.md, map.md đã ghi")
    for warning in warnings:
        print(f"WARN {warning}")
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
