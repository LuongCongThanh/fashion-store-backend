"""Chờ CI của PR rồi in gọn: check đỏ (log vào `logs/ci.log`), SonarCloud, comment gắn dòng.

python3 .claude/skills/ship-ticket-fashion/scripts/ci.py <T> [--pr <số>] [--no-watch]
Exit 0 khi mọi check xanh và SonarCloud 0 New issues, 0 Security Hotspots; ngược lại 1.
Chờ có thể mất vài phút: chạy nền hoặc với timeout dài.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from typing import Any

from common import load_state, resolve, state_dir
from github import REPO, gh, gh_json, pr_checks

PASSING = {"pass", "skipping"}
SONAR_BOT = "sonarqubecloud"
SONAR_CHECK = "SonarCloud Code Analysis"


def check_buckets(checks: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """(check đỏ hoặc huỷ, check còn chạy)."""
    failed = [c for c in checks if c.get("bucket") in {"fail", "cancel"}]
    pending = [c for c in checks if c.get("bucket") == "pending"]
    return failed, pending


def run_id(link: str) -> str | None:
    match = re.search(r"/actions/runs/(\d+)", link or "")
    return match.group(1) if match else None


def sonar_counts(body: str) -> tuple[int, int]:
    def count(label: str) -> int:
        match = re.search(rf"(\d+)\s+{label}", body)
        return int(match.group(1)) if match else 0

    return count(r"New issues?"), count(r"Security Hotspots?")


def sonar_failed_conditions(body: str) -> list[str]:
    """Quality Gate fail: bot liệt kê điều kiện lỗi thay cho số issue."""
    return [
        f"{name} ({rule})"
        for name, rule in re.findall(r"\[([^\]]+)\]\([^)]*\)\s*\((required[^)]*)\)", body)
    ]


def watch(pr: int) -> None:
    for _ in range(10):  # ngay sau push workflow chưa đăng ký check: "no checks reported"
        proc = gh("pr", "checks", str(pr), "--watch", "--interval", "20", check=False)
        if "no checks reported" not in proc.stdout + proc.stderr:
            return
        time.sleep(15)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--pr", type=int, help="mặc định: `pr` trong state")
    parser.add_argument("--no-watch", action="store_true", help="không chờ check chạy xong")
    args = parser.parse_args()
    feature, ticket = resolve(args.ticket)
    pr = args.pr or (load_state(feature.slug, ticket.num) or {}).get("pr")
    if not pr:
        parser.error("chưa có số PR (state.py set <T> pr=<số> hoặc --pr)")

    if not args.no_watch:
        watch(pr)
    checks = pr_checks(pr)
    failed, pending = check_buckets(checks)
    ok = bool(checks) and not failed and not pending
    verdict = "OK" if ok else ("RED" if failed else "WAIT")
    print(f"CI {verdict} · {len(checks)} check · đỏ {len(failed)} · đang chạy {len(pending)}")
    log = state_dir() / "logs" / "ci.log"
    runs = sorted({rid for c in failed if (rid := run_id(c.get("link", "")))})
    if runs:
        log.parent.mkdir(exist_ok=True)
        parts = [gh("run", "view", rid, "--log-failed", check=False).stdout for rid in runs]
        log.write_text("\n".join(parts), encoding="utf-8")
    for c in failed:
        print(f"FAIL {c['name']} · {c.get('link', '')}")
    for c in pending:
        print(f"PENDING {c['name']}")
    if runs:
        print(f"log đỏ: {log}")

    comments = gh_json("pr", "view", str(pr), "--json", "comments")["comments"]
    sonar = next((c["body"] for c in reversed(comments) if c["author"]["login"] == SONAR_BOT), "")
    issues, hotspots = sonar_counts(sonar)
    conditions = sonar_failed_conditions(sonar)
    sonar_red = any(c["name"] == SONAR_CHECK and c["bucket"] not in PASSING for c in checks)
    print(f"SONAR {issues} New issues · {hotspots} Security Hotspots")
    for condition in conditions:
        print(f"SONAR quality gate failed: {condition}")
    if issues or hotspots or conditions or sonar_red:
        sha = gh_json("pr", "view", str(pr), "--json", "headRefOid")["headRefOid"]
        runs_json = gh_json("api", f"repos/{REPO}/commits/{sha}/check-runs")["check_runs"]
        sonar_run = next((r for r in runs_json if r["name"] == SONAR_CHECK), None)
        if sonar_run:
            notes = gh_json("api", f"repos/{REPO}/check-runs/{sonar_run['id']}/annotations")
            for note in notes:
                print(f"SONAR {note['path']}:{note['start_line']} {note['title']}")

    for c in gh_json("api", f"repos/{REPO}/pulls/{pr}/comments"):
        first = (c.get("body") or "").strip().splitlines()[:1]
        print(
            f"COMMENT {c['path']}:{c.get('line')} {c['user']['login']}: {first[0] if first else ''}"
        )
    return 0 if ok and not (issues or hotspots or conditions) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"gh lỗi (exit {exc.returncode}): {(exc.stderr or '').strip()[-300:]}")
        raise SystemExit(2) from None
