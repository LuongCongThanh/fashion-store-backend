"""Kiểm tra trước G2 và trước push theo docs/architecture/11-git-workflow.md.

python3 .claude/skills/ship-ticket-fashion/scripts/check_ship.py <T>
In OK / WARN / FAIL từng mục rồi SHIP OK hoặc SHIP FAIL. Mỗi WARN / FAIL là một điểm của G2.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_ac_trace import trace
from commit_map import problems, read_commits
from common import git, load_state, repo_root, resolve, ticket_ref
from state import validate

BRANCH = re.compile(r"^(feat|fix|refactor|docs|chore|test|hotfix)/[a-z0-9]+(-[a-z0-9]+)*$")
TYPES = "feat|fix|perf|refactor|test|docs|build|ci|chore|revert"
SUBJECT = re.compile(rf"^({TYPES})(\([a-z0-9-]+\))?!?: [a-z0-9`].*[^.]$")
GENERATED = ("/migrations/", "uv.lock", "openapi.yaml")
MAX_LINES = 400


def check_subjects(subjects: list[str]) -> list[str]:
    return [s for s in subjects if not SUBJECT.match(s)]


def diff_size(numstat: str) -> int:
    total = 0
    for line in numstat.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or any(g in path for g in GENERATED):
            continue
        total += int(added) + int(deleted)
    return total


def porcelain_z(root: Path) -> str:
    """`git status --porcelain -z` của repo."""
    return git("-C", str(root), "status", "--porcelain", "-z", strip=False)


def dirty_paths(porcelain_z: str) -> list[str]:
    """Đường dẫn từ `git status --porcelain -z`: không bị trích dẫn kiểu C, rename có thêm
    một mục là đường dẫn cũ (bỏ qua)."""
    entries, paths = porcelain_z.split("\0"), []
    i = 0
    while i < len(entries):
        entry = entries[i]
        if len(entry) > 3:
            paths.append(entry[3:])
            if entry[0] in "RC":
                i += 1
        i += 1
    return paths


def check_dirty(porcelain: list[str], ticket: str) -> list[tuple[str, str]]:
    """`report.md` được commit ở task sync, nên trước đó thư mục ticket dirty chỉ là WARN."""
    others = [path for path in porcelain if not path.startswith(f"{ticket}/")]
    if others:
        return [("FAIL", f"{len(others)} file chưa commit ngoài ticket")]
    if porcelain:
        return [("WARN", "ticket chưa commit (báo cáo commit ở task sync)")]
    return [("OK", "0 file chưa commit")]


def compare_with_dev(ticket: str) -> list[tuple[str, str]]:
    results = []
    behind = int(git("rev-list", "--count", "HEAD..origin/dev") or 0)
    results.append(
        (
            "WARN" if behind else "OK",
            f"sau origin/dev {behind} commit (git fetch trước để chính xác)",
        )
    )

    # commit merge (kéo dev về nhánh) mất khi squash nên không kiểm tên
    subjects = git("log", "--no-merges", "--format=%s", "origin/dev..HEAD").splitlines()
    bad = check_subjects(subjects)
    results.append(
        ("FAIL" if bad else "OK", f"{len(subjects)} commit, {len(bad)} sai Conventional Commits")
    )
    results.extend(("FAIL", f"  commit: {s}") for s in bad)

    commits = read_commits()
    found = problems(commits, ticket)
    worst = "FAIL" if any(level == "FAIL" for level, _ in found) else "WARN" if found else "OK"
    results.append((worst, f"commit → task: {len(commits)} commit, {len(found)} điểm lệch"))
    results.extend((level, f"  {message}") for level, message in found)

    size = diff_size(git("diff", "--numstat", "origin/dev...HEAD"))
    results.append(
        ("WARN" if size > MAX_LINES else "OK", f"{size} dòng đổi (không tính migration, file sinh)")
    )
    return results


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    results: list[tuple[str, str]] = []

    if state is None:
        results.append(("FAIL", "không có state của ticket"))
        state = {}
    else:
        state_problems = validate(state, ticket.ac_total)
        results.append(
            ("FAIL" if state_problems else "OK", f"state schema: {len(state_problems)} điểm thiếu")
        )
        results.extend(("FAIL", f"  {problem}") for problem in state_problems)
        phase = state.get("phase")
        results.append(
            ("OK" if phase in {"sync", "ship"} else "FAIL", f"phase {phase}; cần sync hoặc ship")
        )
        if phase == "ship":
            results.append(("OK" if state.get("gates", {}).get("g2") else "FAIL", "G2 đã duyệt"))
        ac_problems = trace(state, ticket.ac_total, repo_root() / "backend", planned=False)
        results.append(
            ("FAIL" if ac_problems else "OK", f"AC trace: {len(ac_problems)} điểm thiếu")
        )
        results.extend(("FAIL", f"  {problem}") for problem in ac_problems)
        report = ticket.path / "report.md"
        results.append(("OK" if report.is_file() else "FAIL", "report.md tồn tại"))

    branch = git("branch", "--show-current")
    if state and branch != state.get("branch"):
        results.append(("FAIL", f"nhánh {branch} khác nhánh của state {state.get('branch')}"))
    results.append(("OK" if BRANCH.match(branch) else "WARN", f"tên nhánh {branch}"))

    results.extend(check_dirty(dirty_paths(porcelain_z(repo_root())), ticket_ref(ticket)))

    # git() trả "" khi lỗi: thiếu origin/dev thì mọi phép so sánh bên dưới thành 0 và báo OK sai.
    if not git("rev-parse", "--verify", "--quiet", "origin/dev"):
        results.append(("FAIL", "không thấy origin/dev (chạy git fetch origin dev)"))
    else:
        results.extend(compare_with_dev(ticket_ref(ticket)))

    for level, message in results:
        print(f"{level} {message}")
    failed = any(level == "FAIL" for level, _ in results)
    print("SHIP FAIL" if failed else "SHIP OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
