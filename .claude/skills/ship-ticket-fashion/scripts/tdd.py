"""Chạy test của slice và ghi bằng chứng TDD hoặc verification vào state.

python3 .claude/skills/ship-ticket-fashion/scripts/tdd.py <T> <slice> red <test-id>
python3 .claude/skills/ship-ticket-fashion/scripts/tdd.py <T> <slice> green <test-id>
python3 .claude/skills/ship-ticket-fashion/scripts/tdd.py <T> <slice> verify <test-id>
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import UTC, datetime

from common import load_state, repo_root, resolve, save_state, state_dir
from state import validate

INVALID_RED = re.compile(
    r"ERROR collecting|ImportError|ModuleNotFoundError|SyntaxError|fixture '.+?' not found|"
    r"found no collectors|not found:",
    re.I,
)


def red_reason(returncode: int, output: str, expected: str) -> str | None:
    """Red hợp lệ là pytest chạy được test và thất bại ở hành vi/assertion."""
    if returncode != 1:  # pytest: 1 = test failed; 2-5 là interrupt/internal/usage/no-tests
        return None
    if INVALID_RED.search(output):
        return None
    if not expected or expected not in output:
        return None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(("E ", "FAILED ")):
            return stripped[:300]
    return f"pytest failed with expected {expected}"


def find_slice(state: dict, slice_id: str) -> dict | None:
    return next((s for s in state.get("slices", []) if s.get("id") == slice_id), None)


def run_test(test_id: str) -> tuple[int, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(  # noqa: S603 -- test id thuộc plan, argv trực tiếp, không qua shell.
        ["uv", "run", "pytest", test_id, "-x", "-q"],  # noqa: S607 -- uv từ PATH dự án.
        cwd=repo_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("slice")
    parser.add_argument("stage", choices=("red", "green", "verify"))
    parser.add_argument("test_id")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    if state is None:
        print("TỪ CHỐI: không có state")
        return 1
    problems = validate(state, ticket.ac_total)
    if problems:
        print("TỪ CHỐI: state chưa hợp lệ: " + "; ".join(problems))
        return 1
    slice_ = find_slice(state, args.slice)
    if slice_ is None or args.test_id not in slice_.get("tests", []):
        print(f"TỪ CHỐI: {args.test_id} không nằm trong plan của slice {args.slice}")
        return 1
    if state.get("phase") != "code" or slice_.get("status") != "code":
        print("TỪ CHỐI: ticket và slice phải ở phase/status code")
        return 1

    code, output = run_test(args.test_id)
    log = state_dir() / "logs" / f"tdd-{feature.slug}-{ticket.num:02d}-{args.slice}.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text(output, encoding="utf-8")
    evidence = slice_.setdefault("tdd", {}).setdefault(args.test_id, {})
    now = datetime.now(UTC).astimezone().isoformat(timespec="seconds")

    if args.stage == "red":
        if args.test_id not in slice_.get("tddTests", []):
            print("TỪ CHỐI: red chỉ dành cho tddTests")
            return 1
        expected = slice_.get("expectedRed", {}).get(args.test_id, "")
        reason = red_reason(code, output, expected)
        if reason is None:
            print(f"TỪ CHỐI: test chưa red đúng hành vi · log {log}")
            return 1
        evidence.update({"redAt": now, "redReason": reason})
        evidence.pop("greenAt", None)
        save_state(state)
        print(f"RED {args.test_id} · {reason} · log {log}")
        return 0

    if args.stage == "verify":
        if args.test_id not in slice_.get("verificationTests", []):
            print("TỪ CHỐI: verify chỉ dành cho verificationTests")
            return 1
        if code != 0:
            print(f"VERIFY FAIL {args.test_id} · log {log}")
            return 1
        evidence["verifiedAt"] = now
        save_state(state)
        print(f"VERIFIED {args.test_id} · log {log}")
        return 0

    if args.test_id not in slice_.get("tddTests", []):
        print("TỪ CHỐI: green sau red chỉ dành cho tddTests")
        return 1
    if not evidence.get("redAt"):
        print("TỪ CHỐI: chưa có bằng chứng red cho test này")
        return 1
    if code != 0:
        print(f"GREEN FAIL {args.test_id} · log {log}")
        return 1
    evidence["greenAt"] = now
    save_state(state)
    print(f"GREEN {args.test_id} · log {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
