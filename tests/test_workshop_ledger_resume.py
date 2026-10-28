"""Workshop Ledger v1 success scenario (LUCY-004 / protocol scope correction).

Matthew assigns two agents nonoverlapping pieces. Each clocks in, sees the
other's scope and last SHA via work-orders, exchanges one finding through the
board, continues without Lucy, then one exits. After a pause/restart that agent
returns, recovers recent evidence and carries on with NO duplicate work.
Proves awareness + conversation + durable handoff with human-set assignments.
"""
import json
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl, write_json


class SuccessScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"
        self.ledger = pathlib.Path(self.tmp.name) / "ledger"
        self.ledger.mkdir()
        (self.ledger / "active-job.w1.json").write_text(json.dumps({
            "job_id": "pepin-A12", "status": "WORKING", "worker_session_id": "muse-s1",
            "repo": {"branch": "feat/a12", "current_sha": "aaa111"},
            "acceptance": ["parser handles nested helpers"],
            "progress": {"next_action": "profile combined-helper failure"},
        }), encoding="utf-8")
        (self.ledger / "active-job.w2.json").write_text(json.dumps({
            "job_id": "pepin-A14", "status": "WORKING", "worker_session_id": "newton-s1",
            "repo": {"branch": "feat/a14", "current_sha": "bbb222"},
            "acceptance": ["emitter differential clean"],
            "progress": {"next_action": "run clang/gcc differential"},
        }), encoding="utf-8")
        self.feed = pathlib.Path(self.tmp.name) / "msgs.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_agents_coordinate_exit_resume_without_duplicates(self):
        # Both clock in on human-assigned jobs.
        for agent, session, job in (("muse", "muse-s1", "pepin-A12"),
                                    ("newton", "newton-s1", "pepin-A14")):
            rc, card = wl(self.state, "clock-in", "--agent", agent, "--session", session,
                          "--mission", "road-1.0", "--branch", "feat/x",
                          "--sha", "aaa111", "--job", job)
            self.assertEqual(rc, 0)
            self.assertEqual(card["status"], "OPEN")
        # Each sees the other's scope and SHA through the read-only view.
        rc, view = wl(self.state, "work-orders", "--ledger", str(self.ledger))
        self.assertEqual(rc, 0)
        owners = {w["job_id"]: (w["owner_session"], w["sha"]) for w in view["work_orders"]}
        self.assertEqual(owners["pepin-A12"], ("muse-s1", "aaa111"))
        self.assertEqual(owners["pepin-A14"], ("newton-s1", "bbb222"))
        # One useful finding exchanged; both collect it exactly once.
        write_json(self.feed, [{"id": "FIND-001", "text": "nested helpers need flat counter"}])
        for peer in ("outbox-muse.md", "outbox-newton.md"):
            rc, out = wl(self.state, "board-check", "--peer", peer,
                         "--messages", str(self.feed))
            self.assertEqual(rc, 0)
            self.assertEqual([m["id"] for m in out["new_messages"]], ["FIND-001"])
        for peer in ("outbox-muse.md", "outbox-newton.md"):
            _, _ = wl(self.state, "board-ack", "--peer", peer, "--all")
        # Newton exits with a resumable handoff; muse keeps working.
        rc, closed = wl(self.state, "clock-out", "--agent", "newton", "--session", "newton-s1",
                        "--next", "run clang/gcc differential on bbb222",
                        "--evidence", "suite green at bbb222")
        self.assertEqual(rc, 0)
        self.assertEqual(closed["next_action"], "run clang/gcc differential on bbb222")
        # Pause/restart: same state dir, new session. Clean clock-out means no SUSPECT.
        rc, card = wl(self.state, "clock-in", "--agent", "newton", "--session", "newton-s2",
                      "--mission", "road-1.0", "--branch", "feat/a14",
                      "--sha", "bbb222", "--job", "pepin-A14")
        self.assertEqual(rc, 0)
        self.assertEqual(card.get("supersedes_suspect"), [])
        # Resume delivers nothing old (no duplicate work)...
        rc, out = wl(self.state, "board-check", "--peer", "outbox-newton.md",
                     "--messages", str(self.feed))
        self.assertEqual(rc, 0)
        self.assertEqual(out["new_messages"], [])
        # ...but a genuinely new finding still arrives.
        write_json(self.feed, [{"id": "FIND-001", "text": "nested helpers need flat counter"},
                               {"id": "FIND-002", "text": "differential clean on clang"}])
        rc, out = wl(self.state, "board-check", "--peer", "outbox-newton.md",
                     "--messages", str(self.feed))
        self.assertEqual([m["id"] for m in out["new_messages"]], ["FIND-002"])


if __name__ == "__main__":
    unittest.main()
