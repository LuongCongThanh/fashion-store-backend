"""Kiểm môi trường local trước khi làm ticket: Docker, PostgreSQL, migration, seed, Redis, API.

python3 .claude/skills/ship-ticket-fashion/scripts/preflight.py [--fix] [--api-url URL]
In một dòng mỗi mục (`OK` / `FAIL … · fix: <lệnh>`) rồi `PREFLIGHT OK` hoặc `PREFLIGHT FAIL <n>`.
`--fix` chạy các lệnh tự sửa được theo thứ tự (`make up`, `make migrate`, `make load-geo`) rồi kiểm
lại. Mục không tự sửa được (`make run` là server chạy nền, `make create-admin` hỏi mật khẩu,
PostgreSQL ngoài Compose) in lệnh để agent hoặc người dùng chạy. Mốc theo
`docs/architecture/08-local-development.md` mục 2.4.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gitcmd import repo_root

SERVICES = ("worker", "beat", "relay", "redis", "mailpit")
AUTO_FIX_ORDER = ("make up", "make migrate", "make load-geo")
PROBE = """
import json
out = {}
try:
    from django.db import connection
    connection.ensure_connection()
    out["db"] = "ok"
except Exception as exc:
    out["db"] = (type(exc).__name__ + ": " + str(exc)).splitlines()[0][:200]
if out["db"] == "ok":
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    out["pending_migrations"] = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    if not out["pending_migrations"]:
        from modules.identity.constants import AccountKind
        from modules.identity.models import Account
        from shared.geo.models import Province
        out["provinces"] = Province.objects.count()
        out["admins"] = Account.objects.filter(kind=AccountKind.ADMIN).count()
try:
    import redis
    from django.conf import settings
    redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
    out["redis"] = "ok"
except Exception as exc:
    out["redis"] = type(exc).__name__
print("PREFLIGHT_JSON " + json.dumps(out))
"""


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""
    auto: bool = False  # `--fix` tự chạy được


def compose_states(text: str) -> dict[str, tuple[str, int]]:
    """`docker compose ps -a --format json` (từng dòng hoặc một mảng) → service → (state, exit)."""
    text = text.strip()
    if not text:
        return {}
    rows = json.loads(text) if text.startswith("[") else [json.loads(x) for x in text.splitlines()]
    return {r["Service"]: (r.get("State", ""), int(r.get("ExitCode") or 0)) for r in rows}


def evaluate(
    compose: dict[str, tuple[str, int]], django: dict[str, Any], http: dict[str, int | None]
) -> list[Check]:
    checks: list[Check] = []
    down = [s for s in SERVICES if compose.get(s, ("", 0))[0] != "running"]
    migrate = compose.get("migrate")
    if migrate and migrate[1] != 0:
        down.append(f"migrate (exit {migrate[1]})")
    checks.append(
        Check("docker", not down, "chưa chạy: " + ", ".join(down) if down else "", "make up", True)
    )

    db = django.get("db", "không chạy được manage.py")
    checks.append(
        Check(
            "database",
            db == "ok",
            "" if db == "ok" else db,
            "bật PostgreSQL và kiểm DATABASE_URL trong backend/.env (08 mục 2.2, 2.3)",
        )
    )
    if db == "ok":
        pending = int(django.get("pending_migrations", 0))
        checks.append(
            Check(
                "migrations",
                not pending,
                f"{pending} chưa áp" if pending else "",
                "make migrate",
                True,
            )
        )
        if not pending:
            provinces = int(django.get("provinces", 0))
            checks.append(
                Check(
                    "seed geo",
                    provinces > 0,
                    "chưa có tỉnh/thành" if not provinces else "",
                    "make load-geo",
                    True,
                )
            )
            admins = int(django.get("admins", 0))
            checks.append(
                Check(
                    "seed admin",
                    admins > 0,
                    "chưa có Tài khoản Admin" if not admins else "",
                    "make create-admin (người dùng gõ mật khẩu)",
                )
            )
    redis_state = django.get("redis", "không kiểm được")
    checks.append(
        Check(
            "redis",
            redis_state == "ok",
            "" if redis_state == "ok" else redis_state,
            "make up; REDIS_URL=redis://localhost:6380/0 trong backend/.env",
        )
    )

    api_ok = http.get("healthz") == 200 and http.get("readyz") == 200
    api_detail = f"healthz {http.get('healthz')}, readyz {http.get('readyz')}"
    checks.append(Check("api", api_ok, "" if api_ok else api_detail, "make run"))
    mail_ok = http.get("mailpit") == 200
    checks.append(
        Check("mailpit", mail_ok, "" if mail_ok else f"http {http.get('mailpit')}", "make up", True)
    )
    return checks


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def status(url: str) -> int | None:
    if not url.startswith(("http://", "https://")):
        return None
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # noqa: S310 (đã chặn scheme)
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError, OSError:
        return None


def probe(backend: Path, api_url: str) -> list[Check]:
    try:
        compose = compose_states(
            run(["docker", "compose", "ps", "-a", "--format", "json"], backend).stdout
        )
    except OSError, json.JSONDecodeError, subprocess.TimeoutExpired:
        compose = {}
    django: dict[str, Any] = {}
    try:
        proc = run(["uv", "run", "python", "manage.py", "shell", "-c", PROBE], backend)
        line = next((x for x in proc.stdout.splitlines() if x.startswith("PREFLIGHT_JSON ")), "")
        if line:
            django = json.loads(line.removeprefix("PREFLIGHT_JSON "))
        else:
            tail = (proc.stderr.strip().splitlines() or ["manage.py shell lỗi"])[-1]
            django = {"db": tail[:200]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        django = {"db": type(exc).__name__}
    base = api_url.rstrip("/")
    http = {
        "healthz": status(f"{base}/healthz"),
        "readyz": status(f"{base}/readyz"),
        "mailpit": status("http://localhost:8025"),
    }
    return evaluate(compose, django, http)


def next_fix(checks: list[Check], tried: set[str]) -> str | None:
    """Lệnh tự sửa kế tiếp theo thứ tự phụ thuộc, bỏ lệnh đã chạy trong lần này."""
    wanted = {c.fix for c in checks if not c.ok and c.auto}
    return next((cmd for cmd in AUTO_FIX_ORDER if cmd in wanted and cmd not in tried), None)


def report(checks: list[Check]) -> int:
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"OK   {c.name}" if c.ok else f"FAIL {c.name} · {c.detail} · fix: {c.fix}")
    print("PREFLIGHT OK" if not failed else f"PREFLIGHT FAIL {len(failed)}")
    return 1 if failed else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fix", action="store_true", help="chạy make up / migrate / load-geo khi thiếu"
    )
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    backend = repo_root() / "backend"
    checks = probe(backend, args.api_url)
    tried: set[str] = set()
    while args.fix and (command := next_fix(checks, tried)):
        tried.add(command)
        proc = run(command.split(), backend, timeout=900)
        print(f"RUN  {command} · exit {proc.returncode}")
        if proc.returncode != 0:
            print("\n".join((proc.stdout + proc.stderr).strip().splitlines()[-15:]))
            break
        checks = probe(backend, args.api_url)
    return report(checks)


if __name__ == "__main__":
    raise SystemExit(main())
