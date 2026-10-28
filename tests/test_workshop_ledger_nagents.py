"""Workshop Ledger v1 — open-ended participation (LUCY-005).

Agent count is never hard-coded: storage, routing, presence and messaging
treat N agents uniformly. Three simulated identities arrive asynchronously,
all stay visible, each receives a broadcast finding exactly once, a late
arriver gets only what it has not seen, and a departure/resume is clean.
"""
import json
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl, write_json


class OpenEndedParticipationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"
        self.feed = pathlib.Path(self.tmp.name) / "msgs.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_three_agents_arrive_async_coordinate_and_leave_cleanly(self):
        # Agents arrive one by one; each clock-in succeeds regardless of count.
        for agent, session in (("muse", "s1"), ("newton", "s1"), ("ada", "s1")):
            rc, card = wl(self.state, "clock-in", "--agent", agent, "--session", session,
                          "--mission", "road-1.0", "--branch", "feat/x",
                          "--sha", "abc", "--job", "job-%s" % agent)
            self.assertEqual(rc, 0)
            self.assertEqual(card["status"], "OPEN")
        # A broadcast finding reaches every peer cursor exactly once.
        write_json(self.feed, [{"id": "B-001", "text": "seam contract v2"},
                               {"id": "B-002", "text": "sha abc verified"}])
        for agent in ("muse", "newton", "ada"):
            rc, out = wl(self.state, "board-check", "--peer", "outbox-%s.md" % agent,
                         "--messages", str(self.feed))
            self.assertEqual(rc, 0)
            self.assertEqual([m["id"] for m in out["new_messages"]], ["B-001", "B-002"])
        # Third finding: everyone gets only the new one, including a re-checker.
        write_json(self.feed, [{"id": "B-001", "text": "seam contract v2"},
                               {"id": "B-002", "text": "sha abc verified"},
                               {"id": "B-003", "text": "review: no overlap edits"}])
        rc, out = wl(self.state, "board-check", "--peer", "outbox-muse.md",
                     "--messages", str(self.feed))
        self.assertEqual([m["id"] for m in out["new_messages"]], ["B-003"])
        # Ada leaves with a handoff; her cursor persists while others continue.
        rc, closed = wl(self.state, "clock-out", "--agent", "ada", "--session", "s1",
                        "--next", "verify seam contract v2 on next session")
        self.assertEqual(rc, 0)
        self.assertEqual(closed["status"], "CLOSED")
        rc, out = wl(self.state, "board-check", "--peer", "outbox-newton.md",
                     "--messages", str(self.feed))
        self.assertEqual([m["id"] for m in out["new_messages"]], ["B-003"])
        # Ada returns on a new session: clean clock-in, no duplicates, still current.
        rc, card = wl(self.state, "clock-in", "--agent", "ada", "--session", "s2",
                      "--mission", "road-1.0", "--branch", "feat/x",
                      "--sha", "abc", "--job", "job-ada")
        self.assertEqual(rc, 0)
        self.assertEqual(card.get("supersedes_suspect"), [])
        rc, out = wl(self.state, "board-check", "--peer", "outbox-ada.md",
                     "--messages", str(self.feed))
        self.assertEqual(rc, 0)
        self.assertEqual([m["id"] for m in out["new_messages"]], ["B-003"])


if __name__ == "__main__":
    unittest.main()
