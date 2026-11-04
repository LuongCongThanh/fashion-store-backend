import json
import tempfile
import unittest
from pathlib import Path

from metrics import collect, render


def entry(msg_id: str, ts: str, branch: str = "feat/x", output: int = 10, **extra) -> dict:
    usage = {
        "input_tokens": 1,
        "cache_creation_input_tokens": 100,
        "cache_read_input_tokens": 1000,
        "output_tokens": output,
    }
    return {
        "type": "assistant",
        "timestamp": ts,
        "gitBranch": branch,
        "sessionId": "s1",
        "message": {"id": msg_id, "usage": usage},
        **extra,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


STATE = {
    "branch": "feat/x",
    "transitions": [{"from": "grill", "to": "code", "at": "2026-11-04T10:00:00+07:00"}],
}


class Metrics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        write_jsonl(
            root / "s1.jsonl",
            [
                entry("m1", "2026-11-04T02:00:00Z", output=5),  # 09:00 +07 → grill
                entry("m1", "2026-11-04T02:00:01Z", output=7),  # cùng message: lấy dòng cuối
                entry("m2", "2026-11-04T03:30:00Z"),  # 10:30 +07 → code
                entry("m3", "2026-11-04T03:31:00Z", branch="dev"),  # nhánh khác: bỏ
                {"type": "user", "timestamp": "2026-11-04T03:00:00Z", "gitBranch": "feat/x"},
            ],
        )
        sub = root / "s1" / "subagents"
        write_jsonl(sub / "agent-a1.jsonl", [entry("m4", "2026-11-04T03:40:00Z", output=20)])
        (sub / "agent-a1.meta.json").write_text(
            json.dumps({"agentType": "general-purpose", "description": "Implementer S1-S3"}),
            encoding="utf-8",
        )
        self.dirs = [root]

    def tearDown(self):
        self.tmp.cleanup()

    def test_collect_dedupes_messages_filters_branch_and_buckets_phase_and_agent(self):
        report = collect(STATE, self.dirs)
        self.assertEqual(report.by_phase["grill"].turns, 1)
        self.assertEqual(report.by_phase["grill"].output, 7)
        self.assertEqual(report.by_phase["code"].turns, 2)
        self.assertEqual(report.by_agent["Implementer S1-S3"].output, 20)
        self.assertEqual(report.total.turns, 3)
        self.assertEqual(report.total.total, 3 * 1101 + 7 + 10 + 20)

    def test_render_has_phase_and_agent_tables(self):
        text = render(collect(STATE, self.dirs), "backend-bootstrap/16")
        self.assertIn("| grill |", text)
        self.assertIn("| Implementer S1-S3 |", text)
        self.assertIn("| **Tổng** |", text)


if __name__ == "__main__":
    unittest.main()
