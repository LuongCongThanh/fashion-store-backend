"""Mỗi acceptance criterion có slice và test thật chứng minh, hoặc nằm trong `untestable`.

python3 .claude/skills/ship-ticket-fashion/scripts/check_ac_trace.py <T> [--planned]
--planned: chỉ kiểm mọi AC đều có chỗ (phase 1), chưa kiểm test tồn tại.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import load_state, repo_root, resolve


def test_exists(backend: Path, test_id: str) -> bool:
    file, _, rest = test_id.partition("::")
    path = backend / file
    if not path.exists() or not rest:
        return False
    text = path.read_text(encoding="utf-8")
    *classes, name = rest.split("::")
    name = re.sub(r"\[.*\]$", "", name)  # id có tham số: test_x[case]
    return all(re.search(rf"^\s*class {re.escape(c)}\b", text, re.M) for c in classes) and bool(
        re.search(rf"^\s*(async )?def {re.escape(name)}\(", text, re.M)
    )


def trace(state: dict, ac_total: int, backend: Path, planned: bool) -> list[str]:
    problems = []
    untestable = {int(k) for k in state.get("untestable", {})}
    covered: dict[int, list[str]] = {}
    for s in state.get("slices", []):
        for ac in s.get("acs", []):
            covered.setdefault(ac, []).extend(s.get("tests", []))
    for ac in range(1, ac_total + 1):
        if ac in untestable:
            continue
        if ac not in covered:
            problems.append(f"AC {ac}: không thuộc slice nào và không nằm trong untestable")
        elif not planned and not covered[ac]:
            problems.append(f"AC {ac}: slice chưa ghi test nào")
    if not planned:
        for s in state.get("slices", []):
            for test_id in s.get("tests", []):
                if not test_exists(backend, test_id):
                    problems.append(
                        f"{s['id']}: không thấy test {test_id} (đường dẫn tính từ backend/)"
                    )
    return problems


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket")
    parser.add_argument("--planned", action="store_true")
    args = parser.parse_args()

    feature, ticket = resolve(args.ticket)
    state = load_state(feature.slug, ticket.num)
    if state is None:
        print("NO STATE: chạy state.py init trước")
        return 1
    problems = trace(state, ticket.ac_total, repo_root() / "backend", args.planned)
    for p in problems:
        print(f"FAIL {p}")
    print(f"AC TRACE {'OK' if not problems else 'FAIL'} ({ticket.ac_total} AC)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
