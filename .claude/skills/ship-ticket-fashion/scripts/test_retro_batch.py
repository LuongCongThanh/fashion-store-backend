"""Kiểm chứng đếm retro bằng lịch sử Git thật, độc lập backend và GitHub."""

# ruff: noqa: PT009, PT027
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from retro_batch import complete, git_at, status


class RetroBatch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        self.write_ticket(1)
        self.baseline = self.commit()
        self.checkpoint = {"baseline": self.baseline, "batches": []}

    def git(self, *args):
        return git_at(self.root, *args).strip()

    def write_ticket(self, number, state="resolved"):
        path = self.root / f".scratch/f/issues/{number:02d}-ticket/spec.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Ticket\n\nStatus: {state}\n", encoding="utf-8")

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "test: snapshot")
        return self.git("rev-parse", "HEAD")

    def test_nine_new_tickets_and_unmerged_work_do_not_trigger_retro(self):
        for number in range(2, 11):
            self.write_ticket(number)
        self.write_ticket(11, "ready-for-agent")
        snapshot = self.commit()
        self.write_ticket(11)
        result = status(self.root, self.checkpoint, snapshot)
        self.assertEqual(result["pending"], 9)
        self.assertFalse(result["due"])
        with self.assertRaises(ValueError):
            complete(self.root, self.checkpoint, snapshot, result["batch"])

    def test_tenth_ticket_triggers_and_retry_does_not_consume_next_batch(self):
        for number in range(2, 24):
            self.write_ticket(number)
        snapshot = self.commit()
        first = status(self.root, self.checkpoint, snapshot)
        self.assertTrue(first["due"])
        self.assertEqual(len(first["tickets"]), 10)
        updated = complete(self.root, self.checkpoint, snapshot, first["batch"])
        self.assertEqual(complete(self.root, updated, snapshot, first["batch"]), updated)
        second = status(self.root, updated, snapshot)
        self.assertEqual(second["pending"], 12)
        self.assertTrue(second["due"])
        self.assertFalse(set(first["tickets"]) & set(second["tickets"]))

    def test_later_merge_is_preserved_when_completing_frozen_snapshot(self):
        for number in range(2, 12):
            self.write_ticket(number)
        snapshot = self.commit()
        first = status(self.root, self.checkpoint, snapshot)
        self.write_ticket(12)
        self.commit()
        updated = complete(self.root, self.checkpoint, snapshot, first["batch"])
        current = status(self.root, updated, "HEAD")
        self.assertEqual(current["pending"], 1)
        with self.assertRaises(ValueError):
            complete(self.root, self.checkpoint, snapshot, "wrong-id")

    def test_missing_ref_and_baseline_are_errors(self):
        with self.assertRaises(ValueError):
            status(self.root, self.checkpoint, "missing-ref")
        checkpoint = {"baseline": "0" * 40, "batches": []}
        with self.assertRaises(ValueError):
            status(self.root, checkpoint, "HEAD")
