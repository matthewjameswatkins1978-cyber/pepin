"""Workshop Ledger v1 — independent self-review hardening tests.

Caught on a full adversarial re-read of the final helper: same-second double
clock-in, id-less board input, and a corrupt Studio ledger file.
"""
import json
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl, write_json


class ReviewHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"

    def tearDown(self):
        self.tmp.cleanup()

    def test_double_clock_in_same_session_is_idempotent(self):
        kw = dict(agent="muse", session="s1", mission="m",
                  branch="b", sha="aaa", job="j")
        _, c1 = wl(self.state, "clock-in", "--agent", kw["agent"], "--session", kw["session"],
                   "--mission", kw["mission"], "--branch", kw["branch"],
                   "--sha", kw["sha"], "--job", kw["job"])
        rc, c2 = wl(self.state, "clock-in", "--agent", kw["agent"], "--session", kw["session"],
                    "--mission", kw["mission"], "--branch", kw["branch"],
                    "--sha", kw["sha"], "--job", kw["job"])
        self.assertEqual(rc, 0)
        self.assertTrue(c2.get("duplicate"))
        self.assertEqual(c1["id"], c2["id"])
        lines = (self.state / "shifts.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)

    def test_id_less_messages_are_malformed_not_delivered(self):
        feed = pathlib.Path(self.tmp.name) / "msgs.json"
        write_json(feed, [{"noid": 1}, {"id": "m1", "text": "ok"}, {"noid": 2}])
        rc, out = wl(self.state, "board-check", "--peer", "p", "--messages", str(feed))
        self.assertEqual(rc, 0)
        self.assertEqual([m["id"] for m in out["new_messages"]], ["m1"])
        self.assertEqual(out["malformed"], 2)
        _, acked = wl(self.state, "board-ack", "--peer", "p", "--ids", "m1")
        self.assertEqual(acked["cursor"], "m1")  # id-less input never moves the cursor

    def test_corrupt_ledger_is_json_error_not_crash(self):
        ledger = pathlib.Path(self.tmp.name) / "ledger"
        ledger.mkdir()
        (ledger / "active-job.bad.json").write_text("{not json", encoding="utf-8")
        rc, body = wl(self.state, "work-orders", "--ledger", str(ledger))
        self.assertEqual(rc, 1)
        self.assertEqual(body["error"], "LEDGER_CORRUPT")


if __name__ == "__main__":
    unittest.main()
