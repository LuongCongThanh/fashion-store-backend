"""Ghi `plan.md` của ticket từ slice trong state (phase 1, trước G1).

python .claude/skills/ship-ticket-fashion/scripts/plan.py <T>
Ghi đè cả file. Slice đổi thì sửa state rồi chạy lại: state là nguồn, `plan.md` là bản in
cho người đọc ticket và PR.
"""

from __future__ import annotations

import argparse
import sys

from common import load_state, resolve
from progress import PLAN

HEADING = "Kế hoạch"


def cell(items: list) -> str:
    return "<br>".join(f"`{i}`" for i in items) or "—"


def governing_cell(slice_: dict) -> str:
    governing = slice_.get("governingDocs", {})
    return "<br>".join(f"`{path}` → {', '.join(refs)}" for path, refs in governing.items()) or "—"


def tests_cell(slice_: dict) -> str:
    expected = slice_.get("expectedRed", {})
    tdd = [f"TDD `{test}` → {expected.get(test, '?')}" for test in slice_.get("tddTests", [])]
    verification = [f"Verify `{test}`" for test in slice_.get("verificationTests", [])]
    return "<br>".join([*tdd, *verification]) or "—"


def render(state: dict) -> str:
    slices = state.get("slices", [])
    lines = [
        f"# {HEADING}",
        "",
        "Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer "
        "`Task: <task>`.",
        "",
        "| Task | AC | Seam | Test dự kiến | File → tài liệu chi phối | Sau |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {s['id']} | {', '.join(str(a) for a in s.get('acs', [])) or '—'} "
        f"| {s.get('seam', '—')} | {tests_cell(s)} | {governing_cell(s)} "
        f"| {', '.join(s.get('dependsOn', [])) or '—'} |"
        for s in slices
    ]
    for ac, reason in sorted(state.get("untestable", {}).items()):
        lines.append(f"\nAC {ac} không test tự động: {reason}")
    tasks = ["plan", *(s["id"] for s in slices), "R1 (khi review cần sửa)", "sync", "close"]
    lines += ["", "Commit dự kiến: " + " → ".join(f"`{t}`" for t in tasks) + ".", ""]
    return "\n".join(lines)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    if not state or not state.get("slices"):
        print("TỪ CHỐI: state chưa có slice (state.py push <T> 'slices=[…]' trước)")
        return 1
    path = ticket.path / PLAN
    path.write_text(render(state), encoding="utf-8", newline="\n")
    print(f"PLAN {len(state['slices'])} slice → {ticket.path.name}/{PLAN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
