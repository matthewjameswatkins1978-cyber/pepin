"""Workshop Ledger v1 — Finding 2 regression (LUCY-006): explicit consume/ACK.

Delivery and consumption are split: board-check stages messages as pending
(at-least-once: unacked messages replay with redelivered:true after a crash
or restart); board-ack explicitly consumes them and advances the cursor.
Per-recipient state dirs keep cursors independent for the same source outbox.
"""
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl, write_json


class ExplicitAckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"
        self.feed = pathlib.Path(self.tmp.name) / "msgs.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_crash_before_ack_replays_on_restart(self):
        write_json(self.feed, [{"id": "k1", "text": "do not lose me"}])
        rc, out = wl(self.state, "board-check", "--peer", "o.md",
                     "--messages", str(self.feed))
        self.assertEqual([m["id"] for m in out["new_messages"]], ["k1"])
        self.assertFalse(out["new_messages"][0]["redelivered"])
        # Crash: process dies here with NO ack. Restart = fresh process, same dir.
        rc, out2 = wl(self.state, "board-check", "--peer", "o.md",
                      "--messages", str(self.feed))
        self.assertEqual(rc, 0)
        self.assertEqual([m["id"] for m in out2["new_messages"]], ["k1"])
        self.assertTrue(out2["new_messages"][0]["redelivered"])
        self.assertEqual(out2["pending"], 1)
        # Explicit consume stops the replay.
        _, acked = wl(self.state, "board-ack", "--peer", "o.md", "--ids", "k1")
        self.assertEqual(acked["acked"], ["k1"])
        self.assertEqual(acked["cursor"], "k1")
        rc, out3 = wl(self.state, "board-check", "--peer", "o.md",
                      "--messages", str(self.feed))
        self.assertEqual(out3["new_messages"], [])

    def test_two_recipients_share_source_without_consuming_each_other(self):
        other = pathlib.Path(self.tmp.name) / "s2"
        write_json(self.feed, [{"id": "s1", "text": "shared finding"}])
        for state in (self.state, other):
            _, out = wl(state, "board-check", "--peer", "lucy-outbox.md",
                        "--messages", str(self.feed))
            self.assertEqual([m["id"] for m in out["new_messages"]], ["s1"])
        # Muse consumes; Newton's cursor is untouched.
        _, _ = wl(self.state, "board-ack", "--peer", "lucy-outbox.md", "--all")
        _, out = wl(other, "board-check", "--peer", "lucy-outbox.md",
                    "--messages", str(self.feed))
        self.assertEqual([m["id"] for m in out["new_messages"]], ["s1"])
        self.assertTrue(out["new_messages"][0]["redelivered"])

    def test_duplicate_ack_is_idempotent_unknown_is_reported(self):
        write_json(self.feed, [{"id": "d1", "text": "x"}])
        wl(self.state, "board-check", "--peer", "o.md", "--messages", str(self.feed))
        _, first = wl(self.state, "board-ack", "--peer", "o.md", "--ids", "d1")
        self.assertEqual(first["acked"], ["d1"])
        _, second = wl(self.state, "board-ack", "--peer", "o.md",
                       "--ids", "d1,nope")
        self.assertIn("d1", second["acked"])  # duplicate: harmless
        self.assertEqual(second["unknown"], ["nope"])


if __name__ == "__main__":
    unittest.main()
