"""Tiến độ ticket trong .scratch/: trạng thái từng mốc, frontier và cảnh báo lệch.

Nguồn sự thật là dòng `Status:` của từng ticket (docs/agents/issue-tracker.md).
Chạy từ bất kỳ đâu trong repo:
    python3 .claude/skills/ship-ticket-fashion/scripts/progress.py [--feature <slug>]
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from gitcmd import git, repo_root

KNOWN_STATUSES = {
    "needs-triage",
    "needs-info",
    "ready-for-agent",
    "ready-for-human",
    "wontfix",
    "resolved",
    "claimed",
}
MAP = Path(".scratch/mvp-roadmap/map.md")
# Mỗi ticket là thư mục `issues/NN-<slug>/` gồm ba file (docs/agents/issue-tracker.md).
SPEC, PLAN, REPORT = "spec.md", "plan.md", "report.md"


@dataclass
class Ticket:
    num: int
    path: Path  # thư mục ticket
    title: str
    status: str
    blocked_by: list[int]
    ac_done: int
    ac_total: int
    pr: str | None
    blocked_unparsed: list[str] = field(default_factory=list)


@dataclass
class Feature:
    slug: str
    tickets: dict[int, Ticket] = field(default_factory=dict)
    spec_order: list[int] = field(default_factory=list)


def find_section(text: str, heading: str) -> re.Match | None:
    """Thân mục `## <heading>` là group 1, tới heading `## ` kế tiếp hoặc hết file."""
    return re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)


def section(text: str, heading: str) -> str:
    match = find_section(text, heading)
    return match.group(1) if match else ""


def parse_blocked(raw: str) -> tuple[list[int], list[str]]:
    """`NN, NN` (cho phép `[NN-slug](...)`) → (số ticket, phần không đọc được)."""
    nums, unparsed = [], []
    for token in (t.strip() for t in raw.split(",")):
        if not token or token in {"—", "-"}:
            continue
        match = re.fullmatch(r"(\d+)|\[(\d+)[^\]]*\]\([^)]*\)", token)
        if match:
            nums.append(int(match.group(1) or match.group(2)))
        else:
            unparsed.append(token)
    return nums, unparsed


def parse_ticket(path: Path) -> Ticket:
    text = (path / SPEC).read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M)
    status = re.search(r"^Status:\s*(\S+)", text, re.M)
    blocked = re.search(r"^Blocked by:\s*(.+)$", text, re.M)
    pr = re.search(r"\*\*PR:\*\*\s*(#\d+)", text)
    ac = section(text, "Acceptance criteria")
    blocked_by, blocked_unparsed = parse_blocked(blocked.group(1)) if blocked else ([], [])
    return Ticket(
        num=int(path.name.split("-", 1)[0]),
        path=path,
        title=title.group(1).strip() if title else path.name,
        status=status.group(1) if status else "?",
        blocked_by=blocked_by,
        ac_done=len(re.findall(r"^\s*- \[[xX]\]", ac, re.M)),
        ac_total=len(re.findall(r"^\s*- \[[ xX]\]", ac, re.M)),
        pr=pr.group(1) if pr else None,
        blocked_unparsed=blocked_unparsed,
    )


def load_features(root: Path) -> dict[str, Feature]:
    features: dict[str, Feature] = {}
    for issues in sorted((root / ".scratch").glob("*/issues")):
        feature = Feature(slug=issues.parent.name)
        for spec_path in sorted(issues.glob(f"[0-9][0-9]-*/{SPEC}")):
            ticket = parse_ticket(spec_path.parent)
            feature.tickets[ticket.num] = ticket
        spec = issues.parent / "spec.md"
        if spec.exists():
            for num in re.findall(r"issues/(\d+)-", spec.read_text(encoding="utf-8")):
                if int(num) not in feature.spec_order:
                    feature.spec_order.append(int(num))
        features[feature.slug] = feature
    return features


def open_blockers(feature: Feature, ticket: Ticket) -> list[int]:
    return [
        n
        for n in ticket.blocked_by
        if n not in feature.tickets or feature.tickets[n].status != "resolved"
    ]


def frontier(feature: Feature) -> list[Ticket]:
    ready = [
        t
        for t in feature.tickets.values()
        if t.status == "ready-for-agent" and not open_blockers(feature, t)
    ]
    order = {num: i for i, num in enumerate(feature.spec_order)}
    return sorted(ready, key=lambda t: (order.get(t.num, len(order)), t.num))


def warnings(feature: Feature) -> list[str]:
    out = []
    for t in feature.tickets.values():
        name = f"{feature.slug}/{t.num:02d}"
        if t.status not in KNOWN_STATUSES:
            out.append(f"{name}: Status lạ '{t.status}'")
        if t.status == "resolved" and not t.pr:
            out.append(f"{name}: resolved nhưng thiếu dòng **PR:**")
        if t.status == "resolved" and t.ac_done < t.ac_total:
            out.append(f"{name}: resolved nhưng còn {t.ac_total - t.ac_done} AC chưa tick")
        if t.status != "resolved" and t.ac_total and t.ac_done == t.ac_total:
            out.append(f"{name}: đã tick hết AC nhưng Status là {t.status}")
        for n in t.blocked_by:
            if n not in feature.tickets:
                out.append(f"{name}: Blocked by {n:02d} không có thư mục ticket")
        for token in t.blocked_unparsed:
            out.append(f"{name}: Blocked by '{token}' không đọc được (dạng NN, NN)")
    return out


def milestones(root: Path) -> list[tuple[str, str]]:
    path = root / MAP
    if not path.exists():
        return []
    rows = re.findall(
        r"^\|\s*\*\*(M\d+)\*\*\s*\|\s*([^|]+)\|", path.read_text(encoding="utf-8"), re.M
    )
    result = []
    for name, cell in rows:
        slug = re.search(r"`([^`]+)`", cell)
        if slug:
            result.append((name, slug.group(1)))
    return result


def git_state() -> str:
    branch = git("branch", "--show-current")
    dirty = git("status", "--porcelain").splitlines()
    return f"Nhánh: {branch or '(detached)'} · {len(dirty)} file chưa commit"


def print_feature(feature: Feature, label: str = "") -> None:
    tickets = sorted(feature.tickets.values(), key=lambda t: t.num)
    done = sum(t.status == "resolved" for t in tickets)
    print(f"\n## {label}{feature.slug}: {done}/{len(tickets)} resolved")
    for t in tickets:
        blockers = open_blockers(feature, t)
        extra = (
            f" · chặn bởi {', '.join(f'{n:02d}' for n in blockers)}"
            if blockers and t.status != "resolved"
            else ""
        )
        pr = f" {t.pr}" if t.pr else ""
        print(f"  {t.num:02d} [{t.status}] AC {t.ac_done}/{t.ac_total}{pr}{extra} · {t.title}")
    front = frontier(feature)
    print("  Frontier: " + (", ".join(f"{t.num:02d}" for t in front) if front else "(rỗng)"))
    human = [t for t in tickets if t.status == "ready-for-human"]
    if human:
        print("  Cần người làm: " + ", ".join(f"{t.num:02d}" for t in human))
    triage = [t for t in tickets if t.status in {"needs-triage", "needs-info"}]
    if triage:
        print("  Chờ triage: " + ", ".join(f"{t.num:02d} [{t.status}]" for t in triage))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feature", help="chỉ in một feature (tên thư mục trong .scratch/)")
    args = parser.parse_args()

    root = repo_root()
    features = load_features(root)
    print(git_state())

    if args.feature:
        if args.feature not in features:
            print(f"Không có .scratch/{args.feature}/issues/")
            return 1
        print_feature(features[args.feature])
        for w in warnings(features[args.feature]):
            print(f"  ! {w}")
        return 0

    by_slug = {slug: name for name, slug in milestones(root)}
    for slug, feature in features.items():
        label = f"{by_slug[slug]} " if slug in by_slug else ""
        print_feature(feature, label)

    missing = [f"{name} {slug}" for name, slug in milestones(root) if slug not in features]
    if missing:
        print("\nMốc chưa có spec: " + " · ".join(missing))

    all_warnings = [w for f in features.values() for w in warnings(f)]
    if all_warnings:
        print("\nCảnh báo:")
        for w in all_warnings:
            print(f"  ! {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
