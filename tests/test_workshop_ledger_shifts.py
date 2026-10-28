"""Workshop Ledger v1 — Finding 3 regression (LUCY-006): atomic shift writes.

clock-in flagging and clock-out rebuild shift history through one atomic
complete-state replacement (tmp file + move), never delete-then-rebuild. A
failed operation must leave the prior record byte-identical and readable;
other agents' shifts must survive a peer's clock-out; SUSPECT flagging still
marks crashed sessions without inheriting their claims.
"""
import json
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl


class AtomicShiftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"

    def tearDown(self):
        self.tmp.cleanup()

    def shifts_path(self):
        return self.state / "shifts.jsonl"

    def test_failed_clock_out_leaves_history_byte_identical(self):
        wl(self.state, "clock-in", "--agent", "muse", "--session", "s1",
           "--mission", "m", "--branch", "b", "--sha", "a", "--job", "j")
        before = self.shifts_path().read_bytes()
        rc, body = wl(self.state, "clock-out", "--agent", "muse", "--session", "WRONG",
                      "--next", "x")
        self.assertEqual(rc, 2)
        self.assertEqual(body["error"], "NOT_OPEN")
        self.assertEqual(self.shifts_path().read_bytes(), before)
        # Prior record still parses and the shift is still OPEN.
        lines = [json.loads(line) for line in
                 self.shifts_path().read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["status"], "OPEN")

    def test_clock_out_preserves_other_agents_shifts(self):
        wl(self.state, "clock-in", "--agent", "muse", "--session", "s1",
           "--mission", "m", "--branch", "b", "--sha", "a", "--job", "j1")
        wl(self.state, "clock-in", "--agent", "newton", "--session", "s1",
           "--mission", "m", "--branch", "b", "--sha", "a", "--job", "j2")
        rc, closed = wl(self.state, "clock-out", "--agent", "muse", "--session", "s1",
                        "--next", "resume j1")
        self.assertEqual(rc, 0)
        by_agent = {json.loads(line)["agent"]: json.loads(line)
                    for line in self.shifts_path().read_text(encoding="utf-8").splitlines()}
        self.assertEqual(by_agent["muse"]["status"], "CLOSED")
        self.assertEqual(by_agent["muse"]["next_action"], "resume j1")
        self.assertEqual(by_agent["newton"]["status"], "OPEN")

    def test_crash_flagging_survives_atomic_rewrite(self):
        wl(self.state, "clock-in", "--agent", "muse", "--session", "old",
           "--mission", "m", "--branch", "b", "--sha", "a", "--job", "j")
        _, card = wl(self.state, "clock-in", "--agent", "muse", "--session", "new",
                     "--mission", "m", "--branch", "b", "--sha", "a", "--job", "j")
        self.assertEqual(card["status"], "OPEN")
        statuses = [json.loads(line)["status"] for line in
                    self.shifts_path().read_text(encoding="utf-8").splitlines()]
        self.assertIn("SUSPECT (possible crash; not inherited)", statuses)
        self.assertIn("OPEN", statuses)


if __name__ == "__main__":
    unittest.main()
