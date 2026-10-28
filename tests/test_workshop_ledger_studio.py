"""Workshop Ledger v1 — Finding 1 regression (LUCY-006): real Studio layout.

Covers Studio's actual snapshot filenames (src/ledger.ts: active-job.json
unscoped/legacy + active-job.<workerKey>.json scoped), legacy labeling, the
--ledger path contract (<git-common-dir>/matthew-way-studio), recognisable
failure for a wrong/missing location, and a qualified empty view.
"""
import json
import pathlib
import tempfile
import unittest

from tests.test_workshop_ledger import wl


def job(job_id, status="WORKING", session="s1"):
    return {
        "job_id": job_id, "status": status, "worker_session_id": session,
        "repo": {"branch": "b", "current_sha": "abc"},
        "acceptance": ["done when verified"],
        "progress": {"next_action": "verify"},
    }


class StudioLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name) / "s"

    def tearDown(self):
        self.tmp.cleanup()

    def make_ledger(self, name="matthew-way-studio"):
        ledger = pathlib.Path(self.tmp.name) / name
        ledger.mkdir(exist_ok=True)
        return ledger

    def test_scoped_and_legacy_files_both_visible_with_labels(self):
        ledger = self.make_ledger()
        (ledger / "active-job.json").write_text(
            json.dumps(job("legacy-job")), encoding="utf-8")
        (ledger / "active-job.eeaa3db9cf0819eaae0a1ac8.json").write_text(
            json.dumps(job("scoped-job")), encoding="utf-8")
        rc, out = wl(self.state, "work-orders", "--ledger", str(ledger))
        self.assertEqual(rc, 0)
        by_id = {w["job_id"]: w for w in out["work_orders"]}
        self.assertEqual(set(by_id), {"legacy-job", "scoped-job"})
        self.assertIn("legacy/unscoped", by_id["legacy-job"]["scope"])
        self.assertEqual(by_id["scoped-job"]["scope"], "scoped")
        self.assertEqual(by_id["legacy-job"]["source"],
                        "studio-ledger:active-job.json")
        self.assertEqual(out["ledger_layout"], "matthew-way-studio")

    def test_missing_ledger_dir_fails_recognisably(self):
        rc, body = wl(self.state, "work-orders", "--ledger",
                      str(pathlib.Path(self.tmp.name) / "no-such-dir"))
        self.assertEqual(rc, 1)
        self.assertEqual(body["error"], "LEDGER_MISSING")

    def test_wrong_directory_is_flagged_not_silent(self):
        other = self.make_ledger(name="something-else")
        (other / "active-job.json").write_text(
            json.dumps(job("x")), encoding="utf-8")
        rc, out = wl(self.state, "work-orders", "--ledger", str(other))
        self.assertEqual(rc, 0)
        self.assertIn("unexpected", out["ledger_layout"])

    def test_empty_valid_ledger_is_qualified_not_silent(self):
        ledger = self.make_ledger()
        rc, out = wl(self.state, "work-orders", "--ledger", str(ledger))
        self.assertEqual(rc, 0)
        self.assertEqual(out["work_orders"], [])
        self.assertIsNotNone(out["note"])


if __name__ == "__main__":
    unittest.main()
