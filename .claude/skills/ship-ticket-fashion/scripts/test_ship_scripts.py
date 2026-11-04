import unittest

from ci import check_buckets, run_id, sonar_counts, sonar_failed_conditions
from close_ticket import add_history, mark_progress
from github import normalize_check
from merge import merge_blockers

HISTORY = """# Lịch sử ticket

## `backend-bootstrap` (M0)

[Spec](../../.scratch/backend-bootstrap/spec.md)

### Đã xong

1. [06](../../.scratch/backend-bootstrap/issues/06-x/spec.md) · việc sáu · PR #16 · 29/10/2026
2. [07](../../.scratch/backend-bootstrap/issues/07-y/spec.md) · việc bảy · PR #20 · 29/10/2026

### Còn mở

- [14](../../.scratch/backend-bootstrap/issues/14-trivy/spec.md) · quét image bằng trivy · `rfa`
- [20](../../.scratch/backend-bootstrap/issues/20-z/spec.md) · việc hai mươi · `ready-for-agent`

## `other`

### Đã xong

1. [01](../../.scratch/other/issues/01-a/spec.md) · a · PR #1 · 01/10/2026
"""

MAP = """## Notes

| Mốc | Thư mục |
|---|---|
| M0 | [`backend-bootstrap`](../backend-bootstrap/spec.md) · ✅ ghi chú |

## Tiến độ

| Mốc / feature | Trạng thái | Ticket |
|---|---|---|
| **M0** [`backend-bootstrap`](../backend-bootstrap/spec.md) | Xong | ✅ 06, 07 · Backlog: 14, 20 |
| **M1** [`m1`](../module-plans/m1/spec.md) | Đang làm | ✅ 01 · ⬜ 02\u201312 |
"""


class CloseTicket(unittest.TestCase):
    def test_history_appends_done_and_drops_open_line(self):
        text, note = add_history(
            HISTORY, "backend-bootstrap", "14-trivy", 70, "04/11/2026", "fallback"
        )
        self.assertIsNone(note)
        self.assertIn(
            "3. [14](../../.scratch/backend-bootstrap/issues/14-trivy/spec.md)"
            " · quét image bằng trivy · PR #70 · 04/11/2026",
            text,
        )
        self.assertNotIn("- [14]", text)
        self.assertIn("- [20]", text)
        self.assertIn("1. [01](../../.scratch/other", text)  # feature khác giữ nguyên

    def test_history_uses_title_when_ticket_not_listed_open(self):
        text, _ = add_history(HISTORY, "backend-bootstrap", "30-new", 71, "04/11/2026", "tiêu đề")
        self.assertIn(
            "3. [30](../../.scratch/backend-bootstrap/issues/30-new/spec.md) · tiêu đề · PR #71",
            text,
        )

    def test_history_reports_missing_feature(self):
        text, note = add_history(HISTORY, "nope", "01-a", 1, "04/11/2026", "t")
        self.assertEqual(text, HISTORY)
        self.assertIn("nope", note)

    def test_progress_row_gains_ticket_and_flags_leftovers(self):
        text, notes = mark_progress(MAP, "backend-bootstrap", 14)
        self.assertIn("✅ 06, 07, 14 · Backlog: 14, 20", text)
        self.assertTrue(any("Backlog" in n for n in notes))
        text, notes = mark_progress(MAP, "module-plans/m1", 2)
        self.assertIn("✅ 01, 02 · ⬜ 02\u201312", text)
        self.assertTrue(any("02\u201312" in n for n in notes))

    def test_progress_row_already_done_is_unchanged(self):
        text, notes = mark_progress(MAP, "backend-bootstrap", 7)
        self.assertEqual(text, MAP)
        self.assertEqual(notes, [])


class Ci(unittest.TestCase):
    def test_buckets_split_failed_and_pending(self):
        checks = [
            {
                "name": "backend",
                "bucket": "fail",
                "link": "https://github.com/o/r/actions/runs/123/job/9",
            },
            {"name": "lint", "bucket": "pass", "link": ""},
            {"name": "sonar", "bucket": "pending", "link": ""},
            {"name": "skip", "bucket": "skipping", "link": ""},
        ]
        failed, pending = check_buckets(checks)
        self.assertEqual([c["name"] for c in failed], ["backend"])
        self.assertEqual([c["name"] for c in pending], ["sonar"])
        self.assertEqual(run_id(failed[0]["link"]), "123")
        self.assertIsNone(run_id("https://sonarcloud.io/x"))

    def test_sonar_failed_quality_gate_lists_conditions(self):
        body = (
            "**Quality Gate failed**  \nFailed conditions  \n![](x.png '') "
            "[C Security Rating on New Code](https://sonarcloud.io/p?id=1) (required ≥ A)  \n"
            "[See analysis details on SonarQube Cloud](https://sonarcloud.io/d)\n"
        )
        self.assertEqual(
            sonar_failed_conditions(body), ["C Security Rating on New Code (required ≥ A)"]
        )
        self.assertEqual(sonar_counts(body), (0, 0))

    def test_rollup_items_map_to_buckets(self):
        def run(status, conclusion):
            item = {
                "__typename": "CheckRun",
                "name": "b",
                "status": status,
                "conclusion": conclusion,
                "detailsUrl": "u",
            }
            return normalize_check(item)["bucket"]

        self.assertEqual(run("COMPLETED", "SUCCESS"), "pass")
        self.assertEqual(run("COMPLETED", "SKIPPED"), "skipping")
        self.assertEqual(run("COMPLETED", "FAILURE"), "fail")
        self.assertEqual(run("COMPLETED", "CANCELLED"), "cancel")
        self.assertEqual(run("IN_PROGRESS", None), "pending")
        status = {
            "__typename": "StatusContext",
            "context": "ci/x",
            "state": "ERROR",
            "targetUrl": "t",
        }
        self.assertEqual(normalize_check(status), {"name": "ci/x", "bucket": "fail", "link": "t"})

    def test_sonar_counts_from_bot_comment(self):
        body = "Quality Gate passed\n3 New issues\n0 Accepted issues\n1 Security Hotspot\n"
        self.assertEqual(sonar_counts(body), (3, 1))
        self.assertEqual(sonar_counts(""), (0, 0))


OPEN_PR = {"state": "OPEN", "baseRefName": "dev", "isDraft": False, "mergeable": "MERGEABLE"}
DONE_STATE = {"phase": "done", "pr": 70}
GREEN = [{"name": "backend", "bucket": "pass"}]


class Merge(unittest.TestCase):
    def test_green_open_pr_into_dev_merges(self):
        self.assertEqual(merge_blockers(DONE_STATE, OPEN_PR, GREEN), [])

    def test_refuses_other_base_red_checks_and_wrong_phase(self):
        blockers = merge_blockers(
            {"phase": "ship", "pr": 70},
            {**OPEN_PR, "baseRefName": "main"},
            [{"name": "backend", "bucket": "fail"}],
        )
        joined = " ".join(blockers)
        self.assertIn("main", joined)
        self.assertIn("backend", joined)
        self.assertIn("ship", joined)

    def test_refuses_when_no_check_reported(self):
        self.assertTrue(any("check" in b for b in merge_blockers(DONE_STATE, OPEN_PR, [])))

    def test_refuses_conflicts_and_drafts(self):
        pr = {**OPEN_PR, "mergeable": "CONFLICTING", "isDraft": True}
        self.assertEqual(len(merge_blockers(DONE_STATE, pr, GREEN)), 2)


if __name__ == "__main__":
    unittest.main()
