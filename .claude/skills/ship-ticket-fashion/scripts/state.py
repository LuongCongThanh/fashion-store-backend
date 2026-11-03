"""State của ticket đang làm, lưu trong .git/ship-ticket-fashion/ (không bao giờ commit).

  start [<T>]             phase, next, cờ, các dòng READ; chưa có state thì NO STATE
  init <T> --branch <nhánh> --mode lite|full
  set <T> key=value ...   value là JSON nếu parse được; slices.S1.x chọn slice theo id
  push <T> key=value ...  thêm vào field list (value là list thì thêm từng phần tử)
  transition <T> --to <phase> --next "…" --reason "…" [--gate g1|g2]
  check <T>
<T>: <feature>/<NN>, <NN> hoặc thư mục ticket.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import git, load_state, repo_root, resolve, save_state, state_dir, ticket_ref
from progress import PLAN, SPEC, find_section, frontier, load_features

SKILL = ".claude/skills/ship-ticket-fashion"
PHASES = ["grill", "code", "report", "review", "sync", "ship", "done", "retro", "closed"]
BACK_EDGES = {("review", "code"), ("sync", "code"), ("sync", "review")}
GATE_EDGES = {"g1": ("grill", "code"), "g2": ("sync", "ship")}
TRANSITION_ONLY = ("phase", "gates", "transitions")  # set/push không được ghi
FORBIDDEN_RED = re.compile(
    r"^(NameError|AttributeError|TypeError|ImportError|ModuleNotFoundError|SyntaxError|"
    r"OperationalError|InterfaceError|ImproperlyConfigured)(?::|\s|$)"
)
PHASE_FILES = {
    "grill": "1-grill",
    "code": "2-code",
    "report": "3-report",
    "review": "4-review",
    "sync": "5-sync",
    "ship": "6-ship",
    "done": "7-done",
    "retro": "8-retro",
}


# ---- kiểm tra -------------------------------------------------------------


def check_doc_ref(ref: str, root: Path | None = None) -> str | None:
    """Reference có dạng `path.md` hoặc `path.md::số-mục`; file và heading phải tồn tại."""
    if not isinstance(ref, str) or not ref.strip():
        return "reference rỗng"
    path_text, separator, section = ref.partition("::")
    root = root or repo_root()
    path = (root / path_text).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return f"reference ngoài repo: {ref}"
    if path.suffix.lower() != ".md" or not path.is_file():
        return f"không thấy tài liệu: {path_text}"
    if separator:
        if not section.strip():
            return f"reference thiếu mục: {ref}"
        heading = re.compile(rf"^#{{1,6}}\s+{re.escape(section.strip())}(?:\.|\s|$)", re.M)
        if not heading.search(path.read_text(encoding="utf-8")):
            return f"không thấy mục {section} trong {path_text}"
    return None


def governing_refs(state: dict) -> set[str]:
    return {
        ref
        for slice_ in state.get("slices", [])
        for refs in slice_.get("governingDocs", {}).values()
        if isinstance(refs, list)
        for ref in refs
        if isinstance(ref, str)
    }


def carries_tdd_evidence(value: Any) -> bool:
    """Phát hiện bằng chứng tdd lồng trong assignment thay cả slice/list slice."""
    if isinstance(value, dict):
        if value.get("tdd"):
            return True
        return any(carries_tdd_evidence(child) for child in value.values())
    if isinstance(value, list):
        return any(carries_tdd_evidence(child) for child in value)
    return False


def validate(state: dict, ac_total: int | None = None) -> list[str]:
    errors = []
    for key in ("ticket", "feature", "num", "branch", "mode", "phase", "gates", "slices"):
        if key not in state:
            errors.append(f"thiếu field {key}")
    if state.get("phase") not in PHASES:
        errors.append(f"phase lạ: {state.get('phase')}")
    if state.get("mode") not in ("lite", "full"):
        errors.append(f"mode lạ: {state.get('mode')}")

    slices = state.get("slices", [])
    ids = [s.get("id") for s in slices]
    if len(ids) != len(set(ids)):
        errors.append("slice id bị trùng")
    for s in slices:
        slice_id = s.get("id", "?")
        if s.get("status") not in ("todo", "code", "done"):
            errors.append(f"slice {slice_id}: status lạ {s.get('status')}")
        for key in ("acs", "dependsOn", "tests", "tddTests", "verificationTests", "files"):
            if not isinstance(s.get(key), list) or not s.get(key):
                if key in {"dependsOn", "tddTests", "verificationTests"} and isinstance(
                    s.get(key), list
                ):
                    continue
                requirement = (
                    "list"
                    if key in {"dependsOn", "tddTests", "verificationTests"}
                    else "list không rỗng"
                )
                errors.append(f"slice {slice_id}: {key} phải là {requirement}")
        tests = s.get("tests", []) if isinstance(s.get("tests"), list) else []
        tdd_tests = s.get("tddTests", []) if isinstance(s.get("tddTests"), list) else []
        verification = (
            s.get("verificationTests", []) if isinstance(s.get("verificationTests"), list) else []
        )
        if set(tdd_tests) & set(verification):
            errors.append(
                f"slice {slice_id}: test không được nằm ở cả tddTests và verificationTests"
            )
        if set(tests) != set(tdd_tests) | set(verification):
            errors.append(
                f"slice {slice_id}: tests phải bằng hợp của tddTests và verificationTests"
            )
        if len(tests) != len(set(tests)):
            errors.append(f"slice {slice_id}: tests bị trùng")
        expected_red = s.get("expectedRed")
        if not isinstance(expected_red, dict):
            errors.append(f"slice {slice_id}: expectedRed phải là object test → exception")
            expected_red = {}
        for test_id in tdd_tests:
            expected = expected_red.get(test_id)
            if not isinstance(expected, str) or not expected.strip():
                errors.append(f"slice {slice_id}: {test_id} thiếu expectedRed")
            elif FORBIDDEN_RED.match(expected.strip()):
                errors.append(f"slice {slice_id}: {test_id} expectedRed là lỗi hạ tầng/test setup")
        if set(expected_red) != set(tdd_tests):
            errors.append(f"slice {slice_id}: expectedRed phải có đúng key của tddTests")
        if not isinstance(s.get("seam"), str) or not s.get("seam", "").strip():
            errors.append(f"slice {slice_id}: thiếu seam")
        files = s.get("files", []) if isinstance(s.get("files"), list) else []
        governing = s.get("governingDocs")
        if not isinstance(governing, dict):
            errors.append(f"slice {slice_id}: governingDocs phải là object file → mục tài liệu")
        else:
            extra = sorted(set(governing) - set(files))
            if extra:
                errors.append(
                    f"slice {slice_id}: governingDocs có file ngoài plan: {', '.join(extra)}"
                )
            for path in files:
                refs = governing.get(path)
                if not isinstance(refs, list) or not refs:
                    errors.append(f"slice {slice_id}: {path} thiếu governingDocs")
                else:
                    for ref in refs:
                        if problem := check_doc_ref(ref):
                            errors.append(f"slice {slice_id}: {problem}")
        for dep in s.get("dependsOn", []):
            if dep not in ids:
                errors.append(f"slice {slice_id}: dependsOn {dep} không tồn tại")
        for ac in s.get("acs", []):
            if not isinstance(ac, int) or (ac_total is not None and not 1 <= ac <= ac_total):
                errors.append(f"slice {slice_id}: AC {ac} không có trong ticket")
        if s.get("status") == "done":
            evidence = s.get("tdd", {})
            for test_id in tdd_tests:
                record = evidence.get(test_id, {}) if isinstance(evidence, dict) else {}
                if not record.get("redAt") or not record.get("greenAt"):
                    errors.append(f"slice {slice_id}: {test_id} thiếu bằng chứng TDD red/green")
            for test_id in verification:
                record = evidence.get(test_id, {}) if isinstance(evidence, dict) else {}
                if not record.get("verifiedAt"):
                    errors.append(
                        f"slice {slice_id}: {test_id} thiếu bằng chứng verification green"
                    )
    if has_cycle(slices):
        errors.append("dependsOn giữa các slice có vòng lặp")
    current = state.get("currentSlice")
    if current and current not in ids:
        errors.append(f"currentSlice {current} không tồn tại")
    return errors


def has_cycle(slices: list[dict]) -> bool:
    indegree = {s["id"]: 0 for s in slices if "id" in s}
    for s in slices:
        for dep in s.get("dependsOn", []):
            if dep in indegree and s.get("id") in indegree:
                indegree[s["id"]] += 1
    ready = [i for i, d in indegree.items() if d == 0]
    seen = 0
    while ready:
        node = ready.pop()
        seen += 1
        for s in slices:
            if node in s.get("dependsOn", []) and s.get("id") in indegree:
                indegree[s["id"]] -= 1
                if indegree[s["id"]] == 0:
                    ready.append(s["id"])
    return seen != len(indegree)


def check_transition(state: dict, to: str, gate: str | None) -> str | None:
    current = state["phase"]
    if to not in PHASES:
        return f"phase lạ: {to}"
    step_ok = (
        PHASES.index(to) == PHASES.index(current) + 1
        or (current, to) in BACK_EDGES
        or (current, to) == ("done", "closed")
    )
    if not step_ok:
        return f"không đi được {current} → {to}"
    if gate and GATE_EDGES[gate] != (current, to):
        return f"--gate {gate} chỉ dùng cho {' → '.join(GATE_EDGES[gate])}"
    gates = state["gates"]
    if to == "code" and current == "grill" and not (gates.get("g1") or gate == "g1"):
        return "vào code cần G1 (--gate g1)"
    if to == "report" and (
        not state["slices"] or any(s["status"] != "done" for s in state["slices"])
    ):
        return "còn slice chưa done"
    if to == "ship" and not (gates.get("g2") or gate == "g2"):
        return "vào ship cần G2 (--gate g2)"
    if to == "done" and not state.get("pr"):
        return "chưa có số PR (set pr=<số>)"
    if current == "done" and to == "closed" and not state.get("pr"):
        return "đóng ticket cần số PR đã merge"
    return None


def plan_ready(
    spec_text: str, plan_text: str | None, ticket_dirty: bool, state: dict | None = None
) -> str | None:
    """grill → code: `spec.md` có `## Quyết định`, có `plan.md`, cả hai đã commit."""
    missing = [] if find_section(spec_text, "Quyết định") else [f"{SPEC} § Quyết định"]
    if not plan_text:
        missing.append(f"{PLAN} (plan.py)")
    decisions = find_section(spec_text, "Quyết định")
    if state and decisions:
        missing_refs = sorted(ref for ref in governing_refs(state) if ref not in decisions.group(1))
        if missing_refs:
            missing.append("Tài liệu chi phối: " + ", ".join(missing_refs))
    if missing:
        return "ticket thiếu " + ", ".join(missing) + " (phase 1 bước 6-10)"
    if ticket_dirty:
        return f"{SPEC} và {PLAN} chưa commit (commit.py --task plan)"
    return None


# ---- ghi field ------------------------------------------------------------


def parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def locate(state: dict, path: str) -> tuple[Any, str]:
    """Trả (container, key) cho đường dẫn a.b.c; phần tử list chọn theo id."""
    parts = path.split(".")
    node: Any = state
    for part in parts[:-1]:
        if isinstance(node, list):
            match = [x for x in node if isinstance(x, dict) and x.get("id") == part]
            if not match:
                raise SystemExit(f"không có phần tử id={part} trong {path}")
            node = match[0]
        else:
            node = node.setdefault(part, {})
    return node, parts[-1]


def apply(state: dict, assignments: list[str], push: bool) -> None:
    for item in assignments:
        if "=" not in item:
            raise SystemExit(f"cần dạng key=value: {item}")
        path, _, raw = item.partition("=")
        if path.split(".", 1)[0] in TRANSITION_ONLY:
            raise SystemExit(f"{path}: chỉ state.py transition được ghi")
        if path.startswith("slices.") and ".tdd" in path:
            raise SystemExit(f"{path}: chỉ tdd.py được ghi")
        container, key = locate(state, path)
        value = parse_value(raw)
        if carries_tdd_evidence(value):
            raise SystemExit(f"{path}: bằng chứng chỉ tdd.py được ghi")
        if push:
            target = container.setdefault(key, [])
            if not isinstance(target, list):
                raise SystemExit(f"{path} không phải list")
            target.extend(value if isinstance(value, list) else [value])
        else:
            container[key] = value


# ---- lệnh -----------------------------------------------------------------


def require(arg: str) -> tuple[dict, int]:
    feature, ticket = resolve(arg)
    state = load_state(feature.slug, ticket.num)
    if state is None:
        raise SystemExit(f"NO STATE {feature.slug}/{ticket.num:02d}: chạy init trước")
    return state, ticket.ac_total


def cmd_init(args: argparse.Namespace) -> int:
    feature, ticket = resolve(args.ticket)
    if load_state(feature.slug, ticket.num):
        raise SystemExit(f"Đã có state cho {feature.slug}/{ticket.num:02d}")
    state = {
        "ticket": ticket_ref(ticket),
        "feature": feature.slug,
        "num": ticket.num,
        "branch": args.branch,
        "mode": args.mode,
        "phase": "grill",
        "next": "grilling ticket",
        "gates": {"g1": None, "g2": None},
        "slices": [],
        "currentSlice": None,
        "untestable": {},
        "userRequested": [],
        "notes": {},
        "pr": None,
        "transitions": [],
    }
    print(f"STATE {save_state(state)}")
    return 0


def cmd_set(args: argparse.Namespace, push: bool = False) -> int:
    state, ac_total = require(args.ticket)
    apply(state, args.assignments, push)
    errors = validate(state, ac_total)
    if errors:
        print("Không ghi, state sẽ sai:\n" + "\n".join(f"  ERR {e}" for e in errors))
        return 1
    save_state(state)
    print("OK " + ", ".join(a.split("=", 1)[0] for a in args.assignments))
    return 0


def cmd_transition(args: argparse.Namespace) -> int:
    state, ac_total = require(args.ticket)
    # Ticket đã tới done trước khi schema slice chặt hơn được thêm vẫn phải merge/close được.
    invalid = [] if state.get("phase") in {"done", "closed"} else validate(state, ac_total)
    error = "state chưa hợp lệ: " + "; ".join(invalid) if invalid else None
    if error is None:
        error = check_transition(state, args.to, args.gate)
    if error is None and (state["phase"], args.to) == ("grill", "code"):
        folder = repo_root() / state["ticket"]
        plan = folder / PLAN
        # -C: đường dẫn ticket tính từ gốc repo, dù lệnh chạy ở backend/
        dirty = bool(git("-C", str(repo_root()), "status", "--porcelain", "--", state["ticket"]))
        error = plan_ready(
            (folder / SPEC).read_text(encoding="utf-8"),
            plan.read_text(encoding="utf-8") if plan.exists() else None,
            dirty,
            state,
        )
    if error:
        print(f"TỪ CHỐI: {error}")
        return 1
    if (state["phase"], args.to) in BACK_EDGES:
        state["gates"]["g2"] = None  # quay lại sửa thì phải duyệt G2 lần nữa
    now = datetime.now(UTC).astimezone()
    if args.gate:
        state["gates"][args.gate] = now.date().isoformat()
    now = now.isoformat(timespec="seconds")
    state["transitions"].append(
        {"from": state["phase"], "to": args.to, "at": now, "reason": args.reason}
    )
    state["phase"], state["next"] = args.to, args.next
    save_state(state)
    print(f"PHASE {state['transitions'][-1]['from']} → {args.to} · NEXT {args.next}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    state, ac_total = require(args.ticket)
    errors = validate(state, ac_total)
    for e in errors:
        print(f"ERR {e}")
    print("STATE OK" if not errors else f"STATE FAIL ({len(errors)})")
    return 1 if errors else 0


def hooks_installed(hook_path: str) -> bool:
    """File hook do `pre-commit install` ghi; thiếu thì commit không chạy hook nào."""
    return bool(hook_path) and Path(hook_path).is_file()


def pick_active(states: list[dict], branch: str) -> dict | None:
    """states xếp cũ → mới. Ưu tiên ticket chưa closed trên nhánh hiện tại, mới nhất trước."""
    active = [s for s in states if s.get("phase") != "closed"]
    on_branch = [s for s in active if s.get("branch") == branch]
    if on_branch:
        return on_branch[-1]
    return active[0] if len(active) == 1 else None


def find_active() -> dict | None:
    paths = sorted(state_dir().glob("*.json"), key=lambda p: p.stat().st_mtime)
    states = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    return pick_active(states, git("branch", "--show-current"))


def cmd_start(args: argparse.Namespace) -> int:
    if args.ticket:
        feature, ticket = resolve(args.ticket)
        state = load_state(feature.slug, ticket.num)
        if state is None:
            print(f"NO STATE {feature.slug}/{ticket.num:02d} [{ticket.status}] · {ticket.title}")
            print(f"READ {SKILL}/reference/rules.md")
            print(f"READ {SKILL}/phases/1-grill.md")
            return 0
    else:
        state = find_active()
        if state is None:
            print("NO STATE")
            for slug, feature in load_features(repo_root()).items():
                front = frontier(feature)
                if front:
                    rest = ", ".join(f"{t.num:02d}" for t in front[1:])
                    print(
                        f"FRONTIER {slug}: {front[0].num:02d} ({front[0].title})"
                        + (f", {rest}" if rest else "")
                    )
            print(f"READ {SKILL}/reference/rules.md")
            print(f"READ {SKILL}/reference/pick-ticket.md")
            return 0

    flags = []
    branch = git("branch", "--show-current")
    if branch != state["branch"]:
        flags.append(f"BRANCH RED (đang ở {branch}, state là {state['branch']})")
    dirty = len(git("status", "--porcelain").splitlines())
    if dirty:
        flags.append(f"DIRTY {dirty} file")
    behind = git("rev-list", "--count", "HEAD..origin/dev")
    if behind and behind != "0":
        flags.append(f"BEHIND origin/dev {behind} commit")
    open_slices = [s["id"] for s in state["slices"] if s["status"] == "code"]
    if open_slices:
        flags.append(f"SLICE OPEN {', '.join(open_slices)}")
    if state["phase"] == "done" and not state.get("pr"):
        flags.append("NO PR")
    hook = git("rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit")
    if not hooks_installed(hook):
        flags.append("NO HOOKS (chưa cài pre-commit: gitleaks, ruff, mypy chỉ chạy ở CI)")

    gates = state["gates"]
    print(f"TICKET {state['feature']}/{state['num']:02d} · {state['ticket']}")
    pr = state.get("pr") or "—"
    print(f"PHASE {state['phase']} · MODE {state['mode']} · BRANCH {state['branch']} · PR {pr}")
    print(f"NEXT {state['next']}")
    if state["slices"]:
        print("SLICES " + " · ".join(f"{s['id']} {s['status']}" for s in state["slices"]))
    print(f"GATES g1 {gates.get('g1') or '—'} · g2 {gates.get('g2') or '—'}")
    for flag in flags:
        print(f"FLAG {flag}")
    print(f"READ {SKILL}/reference/rules.md")
    if flags or state["phase"] in ("done", "retro", "closed"):
        print(f"READ {SKILL}/reference/resume.md")
    if state["phase"] in PHASE_FILES:
        print(f"READ {SKILL}/phases/{PHASE_FILES[state['phase']]}.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start")
    p.add_argument("ticket", nargs="?")
    p = sub.add_parser("init")
    p.add_argument("ticket")
    p.add_argument("--branch", required=True)
    p.add_argument("--mode", choices=["lite", "full"], required=True)
    for name in ("set", "push"):
        p = sub.add_parser(name)
        p.add_argument("ticket")
        p.add_argument("assignments", nargs="+")
    p = sub.add_parser("transition")
    p.add_argument("ticket")
    p.add_argument("--to", required=True)
    p.add_argument("--next", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--gate", choices=["g1", "g2"])
    p = sub.add_parser("check")
    p.add_argument("ticket")

    args = parser.parse_args(argv)
    handlers = {
        "start": cmd_start,
        "init": cmd_init,
        "set": cmd_set,
        "push": lambda a: cmd_set(a, push=True),
        "transition": cmd_transition,
        "check": cmd_check,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
