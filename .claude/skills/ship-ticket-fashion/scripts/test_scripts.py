"""Test cho các script của skill (stdlib unittest, không cần môi trường backend).

python -m unittest discover -s .claude/skills/ship-ticket-fashion/scripts
"""

# ruff: noqa: PT009, PT027
from __future__ import annotations

import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from check_ac_trace import test_exists, trace
from check_ship import check_dirty, check_subjects, diff_size, dirty_paths, porcelain_z
from close_ticket import close, fill_pr
from commit import check_task, foreign_commits, message
from commit_map import parse_log, problems, render
from common import resolve, state_dir
from plan import render as render_plan
from progress import Feature, frontier, load_features, parse_blocked, parse_ticket
from run_logged import make_recipe
from state import apply, check_transition, hooks_installed, pick_active, plan_ready, validate

TICKET = """# Lớp API

Status: ready-for-agent

Blocked by: 09

Spec: [spec.md](../../spec.md)

## Việc cần làm

- [ ] không phải AC

## Acceptance criteria

- [ ] lỗi trả ErrorDTO
- [x] page_size tối đa 100
"""


def make_state(**overrides) -> dict:
    state = {
        "ticket": "x.md",
        "feature": "f",
        "num": 1,
        "branch": "feat/x",
        "mode": "full",
        "phase": "grill",
        "gates": {"g1": None, "g2": None},
        "slices": [],
        "pr": None,
    }
    state.update(overrides)
    return state


class TicketParsing(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "16-shared-api"
        self.path.mkdir()
        (self.path / "spec.md").write_text(TICKET, encoding="utf-8")

    def test_counts_only_acceptance_criteria(self):
        ticket = parse_ticket(self.path)
        self.assertEqual(
            (ticket.num, ticket.status, ticket.blocked_by), (16, "ready-for-agent", [9])
        )
        self.assertEqual((ticket.ac_done, ticket.ac_total), (1, 2))

    def test_frontier_skips_open_blockers_and_follows_spec_order(self):
        def ticket(num, status, blocked=()):
            return replace(
                parse_ticket(self.path), num=num, status=status, blocked_by=list(blocked)
            )

        feature = Feature(slug="f", spec_order=[15, 12])
        for num, status, blocked in [
            (9, "resolved", ()),
            (12, "ready-for-agent", (9,)),
            (15, "ready-for-agent", ()),
            (16, "ready-for-agent", (15,)),
        ]:
            feature.tickets[num] = ticket(num, status, blocked)
        self.assertEqual([t.num for t in frontier(feature)], [15, 12])

    def test_close_sets_status_pr_and_ticks_only_acceptance_criteria(self):
        text, ticked, _ = close(TICKET, 23)
        self.assertIn("Status: resolved\n\n**PR:** #23", text)
        self.assertIn("- [ ] không phải AC", text)
        self.assertIn("- [x] lỗi trả ErrorDTO", text)
        self.assertEqual(ticked, ["lỗi trả ErrorDTO"])

    def test_close_fills_pr_in_report_and_adds_pr_line_to_spec(self):
        report = "**Nhánh:** `feat/x` · **PR:** chưa mở · **Mode:** lite\n"
        self.assertIn("· **PR:** #31 · **Mode:** lite", fill_pr(report, 31))
        text, _, _ = close(TICKET, 31)
        self.assertIn("Status: resolved\n\n**PR:** #31", text)
        (self.path / "spec.md").write_text(text, encoding="utf-8")
        self.assertEqual(parse_ticket(self.path).pr, "#31")

    def test_resolve_accepts_ticket_folder_or_file_inside_it(self):
        issues = self.dir / ".scratch" / "f" / "issues"
        issues.mkdir(parents=True)
        self.path.rename(issues / "16-shared-api")
        folder = issues / "16-shared-api"
        features = load_features(self.dir)
        self.assertEqual(list(features["f"].tickets), [16])
        for arg in (folder, folder / "spec.md"):
            feature, ticket = resolve(str(arg), features)
            self.assertEqual((feature.slug, ticket.num, ticket.path), ("f", 16, folder))

    def test_close_keeps_existing_pr_line(self):
        text, _, _ = close(TICKET.replace("Status: ready-for-agent", "Status: x\n\n**PR:** #7"), 31)
        self.assertNotIn("#31", text)

    def test_close_leaves_untestable_acs_unticked(self):
        ticket = TICKET.replace("tối đa 100\n", "tối đa 100\n- [ ] cần Redis thật\n")
        text, ticked, skipped = close(ticket, 23, untestable={3})
        self.assertIn("- [ ] cần Redis thật", text)
        self.assertEqual((ticked, skipped), (["lỗi trả ErrorDTO"], ["cần Redis thật"]))

    def test_blocked_by_reads_only_ticket_numbers(self):
        self.assertEqual(parse_blocked("07, 08"), ([7, 8], []))
        self.assertEqual(parse_blocked("[09-add-v2-api](./09-add-v2-api.md)"), ([9], []))
        self.assertEqual(parse_blocked("backend-bootstrap/16"), ([], ["backend-bootstrap/16"]))


class StateMachine(unittest.TestCase):
    def test_code_needs_g1(self):
        self.assertIsNotNone(check_transition(make_state(), "code", None))
        self.assertIsNone(check_transition(make_state(), "code", "g1"))

    def test_rejects_skipping_phases(self):
        self.assertIn("không đi được", check_transition(make_state(), "review", None))

    def test_report_needs_every_slice_done(self):
        state = make_state(phase="code", slices=[{"id": "S1", "status": "code"}])
        self.assertIsNotNone(check_transition(state, "report", None))

    def test_ship_needs_g2_and_review_may_return_to_code(self):
        self.assertIsNotNone(check_transition(make_state(phase="sync"), "ship", None))
        self.assertIsNone(check_transition(make_state(phase="review"), "code", None))

    def test_gate_only_on_its_own_edge(self):
        self.assertIn("--gate g2", check_transition(make_state(phase="report"), "review", "g2"))
        self.assertIn("--gate g1", check_transition(make_state(phase="sync"), "ship", "g1"))
        self.assertIsNone(check_transition(make_state(phase="sync"), "ship", "g2"))

    def test_set_cannot_write_phase_gates_or_transitions(self):
        for item in ("phase=ship", "gates.g2=2026-10-29", "transitions=[]"):
            with self.assertRaises(SystemExit):
                apply(make_state(), [item], push=False)
        with self.assertRaises(SystemExit):
            apply(make_state(), ["transitions={}"], push=True)

    def test_validate_rejects_cycles_and_unknown_acs(self):
        slices = [
            {"id": "S1", "acs": [1], "dependsOn": ["S2"], "status": "todo"},
            {"id": "S2", "acs": [5], "dependsOn": ["S1"], "status": "todo"},
        ]
        errors = validate(make_state(slices=slices), ac_total=2)
        self.assertTrue(any("vòng lặp" in e for e in errors))
        self.assertTrue(any("AC 5" in e for e in errors))

    def test_apply_selects_slice_by_id_and_parses_json(self):
        state = make_state(slices=[{"id": "S1", "status": "todo"}])
        apply(state, ["slices.S1.status=done", "pr=23", "next=S2: viết test"], push=False)
        apply(state, ['slices=[{"id": "S2", "status": "todo"}]'], push=True)
        self.assertEqual(state["slices"][0]["status"], "done")
        self.assertEqual((state["pr"], state["next"]), (23, "S2: viết test"))
        self.assertEqual([s["id"] for s in state["slices"]], ["S1", "S2"])

    def test_pick_active_skips_closed_and_prefers_newest_on_branch(self):
        closed = make_state(num=3, phase="closed")
        older, newer = make_state(num=4, phase="code"), make_state(num=5, phase="grill")
        self.assertIs(pick_active([closed, older, newer], "feat/x"), newer)
        self.assertIsNone(pick_active([closed], "feat/x"))
        self.assertIs(pick_active([closed, older], "feat/other"), older)


class Checks(unittest.TestCase):
    def test_hooks_installed_needs_existing_hook_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            hook = Path(tmp) / "pre-commit"
            self.assertFalse(hooks_installed(str(hook)))
            self.assertFalse(hooks_installed(""))
            hook.write_text("#!/bin/sh\n", encoding="utf-8")
            self.assertTrue(hooks_installed(str(hook)))

    def test_trace_reports_uncovered_ac_and_missing_test(self):
        backend = Path(tempfile.mkdtemp())
        (backend / "tests").mkdir()
        (backend / "tests" / "test_a.py").write_text(
            "class TestA:\n    def test_ok(self):\n", encoding="utf-8"
        )
        state = make_state(
            slices=[
                {
                    "id": "S1",
                    "acs": [1],
                    "tests": ["tests/test_a.py::TestA::test_ok", "tests/test_a.py::test_gone"],
                }
            ],
            untestable={},
        )
        problems = trace(state, ac_total=2, backend=backend, planned=False)
        self.assertTrue(any(p.startswith("AC 2") for p in problems))
        self.assertTrue(any("test_gone" in p for p in problems))
        self.assertTrue(test_exists(backend, "tests/test_a.py::TestA::test_ok"))
        self.assertTrue(test_exists(backend, "tests/test_a.py::TestA::test_ok[00-prefix]"))

    def test_conventional_subjects(self):
        good = [
            "feat(shared): add ErrorDTO handler",
            "docs: close shared core ticket",
            "fix(ci)!: drop x",
        ]
        bad = ["Add stuff", "feat(shared): Add handler", "fix: trailing dot."]
        self.assertEqual(check_subjects(good + bad), bad)

    def test_diff_size_skips_generated_files(self):
        numstat = (
            "10\t2\tbackend/shared/api.py\n"
            "300\t0\tbackend/modules/x/migrations/0001.py\n"
            "5\t5\tuv.lock\n"
        )
        self.assertEqual(diff_size(numstat), 12)

    def test_make_recipe_reads_only_its_target(self):
        makefile = (
            ".PHONY: test lint\n\ntest:\n\tuv run pytest -n auto\n\n"
            "lint:\n\tuv run ruff check .\n\tuv run mypy .\n\nfmt:\n\tuv run ruff format .\n"
        )
        self.assertEqual(
            make_recipe(makefile, "lint"),
            [["uv", "run", "ruff", "check", "."], ["uv", "run", "mypy", "."]],
        )
        self.assertEqual(make_recipe(makefile, "test"), [["uv", "run", "pytest", "-n", "auto"]])

    def test_make_recipe_rejects_unknown_target_and_make_variables(self):
        with self.assertRaises(ValueError):
            make_recipe("test:\n\tuv run pytest\n", "up")
        with self.assertRaises(ValueError):
            make_recipe("up:\n\tdocker compose -f $(FILE) up\n", "up")


REF = ".scratch/f/issues/01-x"


def commit(task: str, sha: str = "a1", refs: str = REF) -> dict:
    return {"sha": sha, "subject": f"feat: {task}", "task": task, "refs": refs, "files": 2}


class PlanAndCommits(unittest.TestCase):
    def test_code_needs_committed_spec_and_plan_files(self):
        self.assertIn("spec.md § Quyết định, plan.md", plan_ready(TICKET, None, ticket_dirty=False))
        spec = TICKET.replace("## Acceptance", "## Quyết định\n\nx\n\n## Acceptance")
        self.assertIn("plan.md", plan_ready(spec, "", ticket_dirty=False))
        self.assertIn("chưa commit", plan_ready(spec, "# Kế hoạch", ticket_dirty=True))
        self.assertIsNone(plan_ready(spec, "# Kế hoạch", ticket_dirty=False))

    def test_plan_renders_whole_plan_file(self):
        state = make_state(
            slices=[{"id": "S1", "acs": [1, 2], "seam": "APIClient", "tests": ["t.py::a"]}],
            untestable={"3": "cần Redis thật"},
        )
        text = render_plan(state)
        self.assertTrue(text.startswith("# Kế hoạch\n\nSinh"))
        self.assertIn("| S1 | 1, 2 | APIClient | `t.py::a` | — | — |", text)
        self.assertIn("AC 3 không test tự động: cần Redis thật", text)
        self.assertIn("`plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`", text)

    def test_commit_message_carries_refs_and_task_trailers(self):
        msg = message("feat(shared): add x", "Vì sao.", REF, "S1")
        self.assertEqual(msg, f"feat(shared): add x\n\nVì sao.\n\nRefs: {REF}\nTask: S1\n")
        self.assertNotIn("\n\n\n", message("docs: plan x ticket", "", REF, "plan"))

    def test_commit_task_must_exist(self):
        state = make_state(slices=[{"id": "S1"}])
        self.assertIsNone(check_task("S1", state))
        self.assertIsNone(check_task("sync", state))
        self.assertIn("S2", check_task("S2", state))
        self.assertIn("task lạ", check_task("fix", state))

    def test_commit_problems_flag_missing_task_other_ticket_and_duplicates(self):
        found = problems(
            [
                commit("S1"),
                commit("", "b2"),
                commit("S1", "c3"),
                commit("R1", "d4", "y.md"),
                commit("ci", "e5"),
                commit("ci", "f6"),
            ],
            REF,
        )
        self.assertEqual([level for level, _ in found], ["FAIL", "WARN", "FAIL"])
        self.assertIn("b2 thiếu trailer Task", found[0][1])
        self.assertIn("task S1 có 2 commit", found[1][1])
        self.assertIn("d4 Refs `y.md`", found[2][1])

    def test_commit_map_orders_by_task_and_shows_acs(self):
        state = make_state(slices=[{"id": "S1", "acs": [1, 3]}])
        table = render(
            [commit("sync", "s9"), commit("S1", "a1"), commit("plan", "p0")], state, True
        )
        rows = table.splitlines()[2:]
        self.assertEqual([r.split(" | ")[0] for r in rows], ["| plan", "| S1", "| sync"])
        self.assertIn("| S1 | 2 code | 1, 3 | `a1` feat: S1 | 2 |", table)

    def test_dirty_ticket_alone_is_only_a_warning(self):
        report = f"{REF}/report.md"
        self.assertEqual(check_dirty([report, f"{REF}/spec.md"], REF)[0][0], "WARN")
        self.assertEqual(check_dirty([report, "backend/x.py"], REF)[0][0], "FAIL")
        self.assertEqual(check_dirty([f"{REF}y/spec.md"], REF)[0][0], "FAIL")
        self.assertEqual(check_dirty([], REF)[0][0], "OK")

    def test_dirty_paths_reads_porcelain_z_unquoted_and_skips_rename_source(self):
        raw = f" M {REF}\0R  new.md\0old.md\0?? .scratch/f/issues/02-á.md\0"
        self.assertEqual(dirty_paths(raw), [REF, "new.md", ".scratch/f/issues/02-á.md"])
        self.assertEqual(dirty_paths(""), [])

    def test_porcelain_keeps_leading_space_of_first_entry(self):
        # strip() từng cắt dấu cách của " M " đầu tiên, làm ticket dirty thành FAIL nhầm
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            setup = (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"])
            for args in setup:
                subprocess.run(["git", "-C", tmp, *args], check=True)
            (repo / ".scratch").mkdir()
            (repo / ".scratch" / "t.md").write_text("a", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "."], check=True)
            subprocess.run(["git", "-C", tmp, "commit", "-qm", "init"], check=True)
            (repo / ".scratch" / "t.md").write_text("b", encoding="utf-8")
            self.assertEqual(dirty_paths(porcelain_z(repo)), [".scratch/t.md"])

    def test_commit_refuses_branch_holding_another_tickets_commit(self):
        # backend-bootstrap/23: phiên khác commit vào nhánh, commit plan chồng lên mà không ai báo
        self.assertIsNone(foreign_commits([commit("plan"), commit("S1", "b2")], REF))
        error = foreign_commits([commit("S1"), commit("", "b2", "")], REF)
        self.assertIn("b2", error)
        self.assertNotIn("a1", error)

    def test_missing_task_is_one_fail_not_also_a_duplicate(self):
        found = problems([commit("", "a1"), commit("", "b2")], REF)
        self.assertEqual([level for level, _ in found], ["FAIL", "FAIL"])

    def test_parse_log_counts_files_from_one_git_log(self):
        raw = (
            f"\x1ea1\x1ffeat: x\x1fS1\x1f{REF}\n\nbackend/a.py\nbackend/b.py\n"
            f"\x1eb2\x1fdocs: y\x1fsync\x1f{REF}\n\n{REF}\n"
        )
        commits = parse_log(raw)
        self.assertEqual([(c["sha"], c["task"], c["files"]) for c in commits],
                         [("a1", "S1", 2), ("b2", "sync", 1)])


class StateSharedAcrossWorktrees(unittest.TestCase):
    def test_worktree_uses_state_dir_of_main_repo(self):
        # backend-bootstrap/23: --absolute-git-dir trỏ vào .git/worktrees/<tên>, state phải copy tay
        import os

        with tempfile.TemporaryDirectory() as tmp:
            main, side = Path(tmp) / "main", Path(tmp) / "side"
            main.mkdir()
            git_in = lambda *a: subprocess.run(  # noqa: E731
                ["git", *a], cwd=main, capture_output=True, check=True
            )
            git_in("init", "-q")
            git_in("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                   "--allow-empty", "-m", "init")
            git_in("worktree", "add", "-q", str(side))
            cwd = os.getcwd()
            try:
                os.chdir(side)
                found = state_dir()
            finally:
                os.chdir(cwd)
            self.assertEqual(found.resolve(), (main / ".git" / "ship-ticket-fashion").resolve())


class CommitOnlyListedPaths(unittest.TestCase):
    """commit.py chạy trong một repo tạm: file đã stage sẵn không lọt vào commit của task."""

    def test_pre_staged_file_stays_out_of_the_task_commit(self):
        import os
        import subprocess

        repo = Path(tempfile.mkdtemp())
        run = lambda *a: subprocess.run(  # noqa: E731
            ["git", *a], cwd=repo, capture_output=True, text=True, check=True
        ).stdout
        run("init", "-q")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        folder = repo / ".scratch" / "f" / "issues" / "01-x"
        folder.mkdir(parents=True)
        (folder / "spec.md").write_text(TICKET, encoding="utf-8")
        run("add", "-A")
        run("commit", "-qm", "chore: init")
        state_dir = repo / ".git" / "ship-ticket-fashion"
        state_dir.mkdir()
        (state_dir / "f-01.json").write_text(
            '{"slices": [{"id": "S1"}]}', encoding="utf-8"
        )
        (repo / "staged.txt").write_text("other task", encoding="utf-8")
        run("add", "staged.txt")
        (repo / "mine.txt").write_text("this task", encoding="utf-8")

        script = Path(__file__).with_name("commit.py")
        out = subprocess.run(
            [os.sys.executable, str(script), "f/01", "--task", "S1", "-m", "feat: add mine",
             "--", "mine.txt"],
            cwd=repo, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertIn("COMMIT", out.stdout, out.stdout + out.stderr)
        self.assertEqual(run("show", "--format=", "--name-only", "HEAD").split(), ["mine.txt"])
        self.assertIn("A  staged.txt", run("status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
