"""Gọi `gh` bằng tài khoản của repo này (máy có nhiều tài khoản GitHub)."""

from __future__ import annotations

import json
import os
import subprocess
from functools import cache
from typing import Any

ACCOUNT = "LuongCongThanh"
REPO = "LuongCongThanh/fashion-store-backend"


@cache
def token() -> str:
    proc = subprocess.run(
        ["gh", "auth", "token", "--user", ACCOUNT], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Token chỉ nằm trong env của tiến trình `gh`, không vào lệnh hay output."""
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "GH_TOKEN": token()},
        check=check,
    )


def gh_json(*args: str) -> Any:
    return json.loads(gh(*args).stdout or "null")


CONCLUSION_BUCKET = {
    "SUCCESS": "pass",
    "NEUTRAL": "pass",
    "SKIPPED": "skipping",
    "CANCELLED": "cancel",
}
STATE_BUCKET = {"SUCCESS": "pass", "PENDING": "pending", "EXPECTED": "pending"}


def normalize_check(item: dict[str, Any]) -> dict[str, str]:
    """Một phần tử `statusCheckRollup` (CheckRun hoặc StatusContext) → name, bucket, link."""
    if item.get("__typename") == "StatusContext":
        bucket = STATE_BUCKET.get(item.get("state") or "", "fail")
        return {
            "name": item.get("context", "?"),
            "bucket": bucket,
            "link": item.get("targetUrl") or "",
        }
    if item.get("status") != "COMPLETED":
        bucket = "pending"
    else:
        bucket = CONCLUSION_BUCKET.get(item.get("conclusion") or "", "fail")
    return {"name": item.get("name", "?"), "bucket": bucket, "link": item.get("detailsUrl") or ""}


def pr_checks(pr: int | str) -> list[dict[str, str]]:
    """Check của PR qua `statusCheckRollup` (gh 2.46 không có `pr checks --json`)."""
    rollup = gh_json("pr", "view", str(pr), "--json", "statusCheckRollup")["statusCheckRollup"]
    return [normalize_check(item) for item in rollup or []]
