#!/usr/bin/env python3
"""Independent fail-closed gate for the Semantic Map's Python authority seam.

Run explicitly: python verification/lucy_semantic_authority_gate.py
The compiler boundary is simulated deliberately; these cases test host policy,
not Pep parsing or typing. No real user file is ever modified.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pep_semantic_map as semantic


def checked_command(operation, *_args, **_kwargs):
    if operation == "inspect":
        return 0, '{"ast": []}', ""
    return 0, '{"status": "valid", "diagnostics": []}', ""


def completed(stdout='{"status": "valid", "diagnostics": []}', code=0):
    return subprocess.CompletedProcess([], code, stdout, "")


class SemanticAuthorityGate(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "fixture.pep"
        self.initial = b"fn main() -> Int { return 0 }\n"
        self.source.write_bytes(self.initial)

    def make_map(self, responder=checked_command):
        with patch.object(semantic, "run_pep_cmd", side_effect=responder):
            return semantic.SemanticMap(self.source)

    def plan(self, smap):
        offset = self.initial.index(b"0")
        return {"repairId": "LUCY-FIXTURE", "diagnosticCode": "PEP_FIXTURE",
                "targetSpan": {"lo": offset, "hi": offset + 1},
                "expectedOriginalBytes": "0", "expectedSourceHash": smap.source_hash,
                "replacement": "1"}

    def apply(self, smap, plan, result=None, error=None):
        with patch.object(semantic, "run_pep_cmd", side_effect=checked_command), \
             patch.object(semantic.subprocess, "run", return_value=result, side_effect=error):
            return smap.apply_repair(plan)

    def test_checked_positive_control(self):
        smap = self.make_map()
        self.assertEqual(smap.epistemic_status, "CHECKED")
        outcome = self.apply(smap, self.plan(smap), completed())
        self.assertEqual(outcome["status"], "SUCCESS")
        self.assertEqual(self.source.read_bytes(), self.initial.replace(b"0", b"1"))

    def test_invalid_candidate_negative_control(self):
        smap = self.make_map()
        outcome = self.apply(smap, self.plan(smap), completed('{"status":"invalid"}', 1))
        self.assertNotEqual(outcome["status"], "SUCCESS")
        self.assertEqual(self.source.read_bytes(), self.initial)

    def test_intervening_edit_never_overwritten(self):
        smap = self.make_map()
        external_edit = self.initial + b"// Another agent's work\n"
        self.source.write_bytes(external_edit)
        outcome = self.apply(smap, self.plan(smap), completed())
        self.assertEqual((outcome["status"], self.source.read_bytes()),
                         ("REJECTED_STALE_REVISION", external_edit))

    def test_malformed_compiler_output_never_authorizes_repair(self):
        smap = self.make_map()
        outcome = self.apply(smap, self.plan(smap), completed("not JSON"))
        self.assertNotEqual(outcome["status"], "SUCCESS")
        self.assertEqual(self.source.read_bytes(), self.initial)

    def test_compiler_launch_failure_preserves_original(self):
        smap = self.make_map()
        try:
            outcome = self.apply(smap, self.plan(smap), error=FileNotFoundError("compiler missing"))
        except OSError:
            # Failure may be returned or raised, but must never leave the source edited.
            outcome = {"status": "FAILED"}
        self.assertNotEqual(outcome["status"], "SUCCESS")
        self.assertEqual(self.source.read_bytes(), self.initial)

    def test_nonzero_check_cannot_certify_map(self):
        def responder(operation, *args, **kwargs):
            if operation == "check":
                return 1, '{"status":"valid","diagnostics":[]}', "failed"
            return checked_command(operation, *args, **kwargs)
        self.assertNotEqual(self.make_map(responder).epistemic_status, "CHECKED")

    def test_unavailable_map_cannot_approve_lane(self):
        smap = self.make_map(lambda *_args: (1, "", "unavailable"))
        self.assertNotEqual(smap.epistemic_status, "CHECKED")
        self.assertFalse(smap.verify_lane({"laneId": "review"})["laneValid"])

    def test_unavailable_base_or_branch_cannot_approve_merge(self):
        good = self.make_map()
        bad = self.make_map(lambda *_args: (1, "", "unavailable"))
        for maps in ((bad, good, good), (good, bad, good), (good, good, bad)):
            with self.subTest(statuses=[m.epistemic_status for m in maps]):
                self.assertTrue(semantic.SemanticMap.detect_semantic_conflicts(*maps)["hasConflicts"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
