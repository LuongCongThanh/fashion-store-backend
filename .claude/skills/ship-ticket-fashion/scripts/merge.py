"""Squash merge PR của ticket vào `dev` khi người dùng đã bảo merge, rồi đóng phase 7.

python3 .claude/skills/ship-ticket-fashion/scripts/merge.py <T> [--dry-run]
Từ chối khi phase khác `done`, PR không mở, base khác `dev`, còn conflict, là draft, hoặc
check chưa xanh. Lệnh `gh pr merge` chạy trong script nên hook guard_merge_target không thấy
nó; script tự giữ đúng quy tắc của hook: chỉ merge PR vào `dev`.
Rồi: thân squash = `commit_map.py --md`, `git switch dev && git pull --ff-only`,
`progress.py`, `state.py transition --to closed`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import load_state, repo_root, resolve
from github import gh, gh_json, pr_checks

ALLOWED_BASE = "dev"  # cùng giá trị với .claude/hooks/guard_merge_target.py
SCRIPTS = Path(__file__).resolve().parent


def merge_blockers(state: dict[str, Any], pr: dict[str, Any], checks: list[dict]) -> list[str]:
    blockers = []
    if state.get("phase") != "done":
        blockers.append(f"phase là {state.get('phase')}, cần done")
    if pr.get("state") != "OPEN":
        blockers.append(f"PR đang {pr.get('state')}")
    if pr.get("baseRefName") != ALLOWED_BASE:
        blockers.append(f"base là `{pr.get('baseRefName')}`: chỉ merge PR vào `{ALLOWED_BASE}`")
    if pr.get("isDraft"):
        blockers.append("PR còn là draft")
    if pr.get("mergeable") == "CONFLICTING":
        blockers.append("PR có conflict với base")
    if not checks:
        blockers.append("PR chưa có check nào: chờ CI (ci.py)")
    not_green = [c["name"] for c in checks if c.get("bucket") not in {"pass", "skipping"}]
    if not_green:
        blockers.append("check chưa xanh: " + ", ".join(not_green))
    return blockers


def script(*args: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / args[0]), *args[1:]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--dry-run", action="store_true", help="chỉ kiểm, không merge")
    args = parser.parse_args()
    feature, ticket = resolve(args.ticket)
    t = f"{feature.slug}/{ticket.num:02d}"
    state = load_state(feature.slug, ticket.num) or {}
    if not state.get("pr"):
        parser.error("state chưa có số PR")
    pr_no = str(state["pr"])
    pr = gh_json("pr", "view", pr_no, "--json", "state,baseRefName,isDraft,mergeable,url")
    checks = pr_checks(pr_no)
    blockers = merge_blockers(state, pr, checks)
    if blockers:
        print(f"TỪ CHỐI merge PR #{pr_no}:")
        print("\n".join(f"  - {b}" for b in blockers))
        return 1
    if args.dry_run:
        print(f"OK merge được PR #{pr_no} ({pr['url']})")
        return 0

    body = repo_root() / ".git" / "SQUASH_BODY.md"
    body.write_text(script("commit_map.py", t, "--md"), encoding="utf-8")
    gh("pr", "merge", pr_no, "--squash", "--delete-branch", "-F", str(body))
    print(f"MERGED PR #{pr_no} vào {ALLOWED_BASE}")
    for cmd in (["switch", ALLOWED_BASE], ["pull", "--ff-only"]):
        subprocess.run(["git", *cmd], cwd=repo_root(), check=True, capture_output=True)
    print(script("progress.py", "--feature", feature.slug).strip().splitlines()[0])
    script(
        "state.py",
        "transition",
        t,
        "--to",
        "closed",
        "--next",
        "chọn ticket tiếp theo",
        "--reason",
        f"merged PR #{pr_no}",
    )
    print(f"{t}: phase closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or exc.stdout or "").strip()[-400:]
        print(f"LỖI ở `{' '.join(map(str, exc.cmd[:3]))}…` (exit {exc.returncode}): {tail}")
        raise SystemExit(2) from None
