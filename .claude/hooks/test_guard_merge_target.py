"""Test cho guard_merge_target.py (stdlib unittest; `gh` và `git` được giả lập).

python -m unittest discover -s .claude/hooks
"""

# ruff: noqa: PT009
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import guard_merge_target as guard

BASES = {"33": "dev", "18": "uat", "40": "main", None: "dev"}
M = "gh pr merge"
P = "git push"


class Guard(unittest.TestCase):
    def setUp(self):
        self.branch, self.upstream = "feat/x", "feat/x"
        patches = [
            mock.patch.object(guard, "pr_base", lambda sel, repo: BASES.get(sel, "")
                              if repo in (None, "LuongCongThanh/fashion-store-backend")
                              else "main"),
            mock.patch.object(guard, "current_branch", lambda cwd: self.branch),
            mock.patch.object(guard, "upstream_branch", lambda cwd: self.upstream),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def blocked(self, command: str) -> bool:
        return guard.check(command) is not None

    def test_allows_normal_work(self):
        for command in [
            "ls -la",
            f'GH_TOKEN="$(gh auth token --user LuongCongThanh)" {M} 33 --squash -F .git/SQUASH_BODY.md',
            f"{P} -u origin feat/x",
            f"{P}",
            f'echo "dùng {M} 18"',
            "gh pr create -B dev -F .git/PR_BODY.md",
            "gh api repos/a/b/pulls/18/comments",
        ]:
            with self.subTest(command):
                self.assertFalse(self.blocked(command))

    def test_blocks_merge_into_uat_or_main(self):
        for command in [
            f"{M} 18 --merge",
            f'cd x; GH_TOKEN="$(gh auth token --user A)" {M} 18 --merge',
            f"env {M} 40",
            f"time {M} 40",
            f"xargs {M} 40",
            f"gh.exe pr merge 40",
            f'bash -c "{M} 40"',
            f"{M} 33 --repo=org/other",
            f"{M} 33 -Rorg/other",
            f"{M} 77",  # không tra được base
        ]:
            with self.subTest(command):
                self.assertTrue(self.blocked(command))

    def test_blocks_merge_through_gh_api(self):
        for command in [
            "gh api -X PUT repos/a/b/pulls/18/merge",
            "gh api -X POST repos/a/b/merges -f base=main -f head=dev",
            "gh api graphql -f query='mutation{mergePullRequest(input:{pullRequestId:\"x\"}){clientMutationId}}'",
            "gh api graphql -F query=@merge.graphql",
        ]:
            with self.subTest(command):
                self.assertTrue(self.blocked(command))
        self.assertFalse(self.blocked("gh api graphql -f query='{viewer{login}}'"))

    def test_blocks_push_to_protected_branch(self):
        for command in [
            f"{P} origin HEAD:uat",
            f"git fetch && {P} origin main",
            f"{P} origin +refs/heads/main",
            "git -C . push origin main",
            "git -c core.x=y push origin uat",
            f"git checkout main && git merge dev && {P}",
            f"git switch uat; {P} origin HEAD",
            f"{P} --all origin",
        ]:
            with self.subTest(command):
                self.assertTrue(self.blocked(command))

    def test_bare_push_checks_current_branch_and_upstream(self):
        self.branch = "main"
        self.assertTrue(self.blocked(P))
        self.assertTrue(self.blocked(f"{P} origin HEAD"))
        self.branch, self.upstream = "feat/x", "uat"
        self.assertTrue(self.blocked(f"{P} origin"))

    def test_heredoc_body_is_data_unless_a_shell_runs_it(self):
        body = f"chặn `{M}` khi base, {P} origin main, gh api x/pulls/1/merge"
        self.assertFalse(self.blocked(f"cat > .git/PR_BODY.md <<'EOF'\n{body}\nEOF\ngh pr create"))
        self.assertTrue(self.blocked(f"cat > b <<'EOF'\nx\nEOF\n{P} origin uat"))
        self.assertTrue(self.blocked(f"bash <<'EOF'\n{M} 40 --squash\nEOF"))
        self.assertTrue(self.blocked(f"cat <<'EOF' | sh\n{P} origin HEAD:main\nEOF"))


class HookProcess(unittest.TestCase):
    """Chạy hook như Claude Code: JSON qua stdin, exit 2 là chặn."""

    def run_hook(self, stdin: bytes) -> int:
        script = Path(__file__).with_name("guard_merge_target.py")
        return subprocess.run([sys.executable, str(script)], input=stdin,
                              capture_output=True).returncode

    def test_vietnamese_command_is_read_as_utf8(self):
        payload = json.dumps({"tool_input": {"command": "echo 'đã xong'"}}, ensure_ascii=False)
        self.assertEqual(self.run_hook(payload.encode("utf-8")), 0)

    def test_hook_error_blocks(self):
        self.assertEqual(self.run_hook(b"not json"), 2)


@unittest.skipUnless(shutil.which("sh"), "cần sh (Linux, macOS, Git Bash)")
class RunPyWrapper(unittest.TestCase):
    """settings.json gọi hook qua run_py.sh: stdin và exit code phải đi qua nguyên vẹn."""

    def run_wrapped(self, stdin: bytes) -> int:
        here = Path(__file__).parent
        return subprocess.run(["sh", str(here / "run_py.sh"), str(here / "guard_merge_target.py")],
                              input=stdin, capture_output=True).returncode

    def test_allowed_command_passes(self):
        payload = json.dumps({"tool_input": {"command": "git status"}})
        self.assertEqual(self.run_wrapped(payload.encode("utf-8")), 0)

    def test_hook_error_still_blocks(self):
        self.assertEqual(self.run_wrapped(b"not json"), 2)


if __name__ == "__main__":
    unittest.main()
