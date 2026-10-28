"""Workshop Ledger v1 — peer claim scenario tests (LUCY-003 autonomy requirement).

Proves, on one machine with a single-writer coordinator lock: two agents see
the same roadmap-backed queue, pick non-overlapping GREEN tasks, record the
assignment through one authoritative claim path, and cannot seize, steal, or
auto-claim AMBER/RED/blocked work. A real two-process race on one job leaves
exactly one holder.
"""
import json
import pathlib
import subprocess
import tempfile
import unittest

from tests.test_workshop_ledger import wl, write_json

ROOT = pathlib.Path(__file__).resolve().parents[1]
WL = ROOT / "workshop-ledger" / "wl.ps1"
PWSH = r"C:\Program Files\PowerShell\7\pwsh.exe"

QUEUE = {
    "generation": 1,
    "jobs": [
        {"id": "G1", "status": "READY", "risk": "GREEN", "deps": [],
         "acceptance": "helper A tested"},
        {"id": "G2", "status": "READY", "risk": "GREEN", "deps": ["G1"],
         "acceptance": "helper B tested after A"},
        {"id": "A1", "status": "READY", "risk": "AMBER", "deps": [],
         "acceptance": "cross-file handoff"},
        {"id": "R1", "status": "READY", "risk": "RED", "deps": [],
         "acceptance": "merge to main"},
    ],
    "claims": [],
}


class ClaimScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"
        self.queue = pathlib.Path(self.tmp.name) / "queue.json"
        write_json(self.queue, QUEUE)

    def tearDown(self):
        self.tmp.cleanup()

    def gen(self):
        rc, view = wl(self.state, "queue-view", "--ledger", str(self.queue))
        self.assertEqual(rc, 0)
        return view["generation"]

    def test_peers_pick_non_overlapping_green(self):
        g = self.gen()
        rc, c1 = wl(self.state, "claim", "--ledger", str(self.queue), "--job", "G1",
                    "--agent", "muse", "--session", "s1", "--expect-cursor", str(g))
        self.assertEqual(rc, 0)
        rc, c2 = wl(self.state, "claim", "--ledger", str(self.queue), "--job", "G2",
                    "--agent", "lucy", "--session", "s2",
                    "--expect-cursor", str(c1["generation"]))
        # G2 depends on G1 which is HELD, not DONE: must park, not start.
        self.assertEqual(rc, 2)
        self.assertEqual(c2["error"], "BLOCKED")

    def test_race_on_one_job_single_winner(self):
        g = self.gen()
        procs = [
            subprocess.Popen(
                [PWSH, "-NoProfile", "-NonInteractive", "-File", str(WL),
                 "--state", str(self.state), "claim", "--ledger", str(self.queue),
                 "--job", "G1", "--agent", a, "--session", s,
                 "--expect-cursor", str(g)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for a, s in (("muse", "s1"), ("lucy", "s2"))]
        outs = [p.communicate(timeout=120) for p in procs]
        codes = [p.returncode for p in procs]
        self.assertEqual(sorted(codes), [0, 2])
        winner = json.loads(outs[codes.index(0)][0])
        loser = json.loads(outs[codes.index(2)][0])
        self.assertFalse(winner["duplicate"])
        self.assertEqual(loser["error"], "CONFLICT")
        q = json.loads(self.queue.read_text(encoding="utf-8"))
        held = [c for c in q["claims"] if c["job"] == "G1" and c["status"] == "HELD"]
        self.assertEqual(len(held), 1)

    def test_duplicate_claim_is_idempotent(self):
        g = self.gen()
        kw = dict(ledger=str(self.queue), job="G1", agent="muse", session="s1")
        _, c1 = wl(self.state, "claim", "--ledger", kw["ledger"], "--job", kw["job"],
                   "--agent", kw["agent"], "--session", kw["session"],
                   "--expect-cursor", str(g))
        rc, c2 = wl(self.state, "claim", "--ledger", kw["ledger"], "--job", kw["job"],
                    "--agent", kw["agent"], "--session", kw["session"],
                    "--expect-cursor", str(c1["generation"]))
        self.assertEqual(rc, 0)
        self.assertTrue(c2["duplicate"])
        q = json.loads(self.queue.read_text(encoding="utf-8"))
        held = [c for c in q["claims"] if c["job"] == "G1" and c["status"] == "HELD"]
        self.assertEqual(len(held), 1)

    def test_stale_generation_rejected(self):
        g = self.gen()
        wl(self.state, "claim", "--ledger", str(self.queue), "--job", "G1",
           "--agent", "muse", "--session", "s1", "--expect-cursor", str(g))
        rc, body = wl(self.state, "claim", "--ledger", str(self.queue), "--job", "G1",
                      "--agent", "lucy", "--session", "s2", "--expect-cursor", str(g))
        self.assertEqual(rc, 2)
        self.assertEqual(body["error"], "CONFLICT")

    def test_amber_red_need_humans_not_auto_claim(self):
        g = self.gen()
        for job, err in (("A1", "NEEDS_AUTH"), ("R1", "NEEDS_AUTH")):
            rc, body = wl(self.state, "claim", "--ledger", str(self.queue),
                          "--job", job, "--agent", "muse", "--session", "s1",
                          "--expect-cursor", str(g))
            self.assertEqual(rc, 2, job)
            self.assertEqual(body["error"], err, job)

    def test_peer_cannot_release_or_seize(self):
        g = self.gen()
        wl(self.state, "claim", "--ledger", str(self.queue), "--job", "G1",
           "--agent", "muse", "--session", "s1", "--expect-cursor", str(g))
        rc, body = wl(self.state, "release", "--ledger", str(self.queue), "--job", "G1",
                      "--agent", "lucy", "--session", "s2")
        self.assertEqual(rc, 2)
        self.assertEqual(body["error"], "NOT_OWNER")
        # Holder releases; job returns to READY for a later safe pick.
        rc, out = wl(self.state, "release", "--ledger", str(self.queue), "--job", "G1",
                     "--agent", "muse", "--session", "s1")
        self.assertEqual(rc, 0)
        _, view = wl(self.state, "queue-view", "--ledger", str(self.queue))
        g1 = [j for j in view["jobs"] if j["id"] == "G1"][0]
        self.assertEqual(g1["effective"], "READY")


if __name__ == "__main__":
    unittest.main()
