"""Adversarial tests for the first-party Pep test runner (V8 slice 1).

Proves the runner classifies honestly: mismatches fail, wrong rejection
codes fail, valid programs never pass as negatives, crashes/timeouts/
transport failures never count as passes, malformed inputs are infra
errors, and selection executes subsets.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test-runner" / "pep_test.py"
REAL_MANIFEST = ROOT / "test-runner" / "manifest.json"


def run_runner(*args, manifest=None, pep=None, timeout=300):
    cmd = [sys.executable, str(RUNNER), "--manifest",
           str(manifest or REAL_MANIFEST)]
    if pep:
        cmd += ["--pep", str(pep)]
    cmd += [str(a) for a in args]
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def write_manifest(tmp, fixtures, **extra):
    doc = {"schemaVersion": 1, "fixtures": fixtures}
    doc.update(extra)
    path = pathlib.Path(tmp) / "m.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


class RunnerHonestyTests(unittest.TestCase):
    def test_real_manifest_passes_end_to_end(self):
        proc = run_runner("--json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["schemaVersion"], 1)
        self.assertEqual(doc["counts"]["pass"], 6)
        self.assertEqual(doc["counts"]["skip"], 1)
        self.assertEqual(doc["counts"]["fail"], 0)
        for t in doc["tests"]:
            self.assertIn("source_sha256", t)
        self.assertTrue(doc["repoRevision"])
        self.assertEqual(doc["backend"], "interpreter")

    def test_stdout_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "w.pep").write_text('say(int_text(1 + 1))\n',
                                                     encoding="utf-8")
            m = write_manifest(tmp, [{"id": "x", "file": "w.pep", "kind": "run",
                                      "expect": {"exit": 0, "stdout": "3\n"}}])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            self.assertEqual(doc["tests"][0]["status"], "fail")
            self.assertNotEqual(proc.returncode, 0)

    def test_wrong_code_and_valid_program_never_pass_negatives(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = pathlib.Path(tmp) / "good.pep"
            good.write_text('say(int_text(1))\n', encoding="utf-8")
            bad = pathlib.Path(tmp) / "bad.pep"
            bad.write_text('fn main() -> Int { return "s" }\n', encoding="utf-8")
            m = write_manifest(tmp, [
                {"id": "n1", "file": "bad.pep", "kind": "reject",
                 "expect": {"code": "PEP_UNKNOWN_FUNCTION"}},
                {"id": "n2", "file": "good.pep", "kind": "reject",
                 "expect": {"code": "PEP_TYPE_MISMATCH"}},
            ])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            by_id = {t["id"]: t for t in doc["tests"]}
            self.assertEqual(by_id["n1"]["status"], "fail")  # right reject, wrong code
            self.assertEqual(by_id["n2"]["status"], "fail")  # valid program, never a negative pass
            self.assertNotEqual(proc.returncode, 0)

    def test_crash_never_counts_as_negative_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            crash = pathlib.Path(tmp) / "c.pep"
            crash.write_text('say(int_text(1 / 0))\n', encoding="utf-8")
            m = write_manifest(tmp, [
                {"id": "c1", "file": "c.pep", "kind": "reject",
                 "expect": {"code": "PEP_RUNTIME_DIVISION_BY_ZERO"}},
            ])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            # div-by-zero CHECKS valid, so a reject fixture must fail, not pass.
            self.assertEqual(doc["tests"][0]["status"], "fail")
            self.assertNotEqual(proc.returncode, 0)

    def test_missing_fixture_and_malformed_manifest_are_infra(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = write_manifest(tmp, [{"id": "m1", "file": "nope.pep",
                                       "kind": "run", "expect": {"exit": 0}}])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            self.assertEqual(doc["tests"][0]["status"], "infra_error")
            bad = pathlib.Path(tmp) / "bad.json"
            bad.write_text("{oops", encoding="utf-8")
            proc2 = run_runner("--json", manifest=bad)
            self.assertEqual(proc2.returncode, 2)
            self.assertIn("infra_error", proc2.stdout)

    def test_printed_code_is_not_a_diagnostic(self):
        # A program that merely prints the expected code word must NOT pass
        # as demonstrating the runtime diagnostic (line:col: CODE: shape required).
        with tempfile.TemporaryDirectory() as tmp:
            fake = pathlib.Path(tmp) / "fake.pep"
            fake.write_text('say("PEP_RUNTIME_DIVISION_BY_ZERO")\n',
                            encoding="utf-8")
            m = write_manifest(tmp, [{"id": "f1", "file": "fake.pep", "kind": "run",
                                      "expect": {"exit": 0, "stdout": "PEP_RUNTIME_DIVISION_BY_ZERO\n",
                                                 "diagnosticCode": "PEP_RUNTIME_DIVISION_BY_ZERO"}}])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            # exit/stdout match but no diagnostic line exists: must fail, not pass.
            self.assertEqual(doc["tests"][0]["status"], "fail")
            self.assertNotEqual(proc.returncode, 0)

    def test_timeout_and_garbage_output_never_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            sleeper = pathlib.Path(tmp) / "hang.py"
            sleeper.write_text(
                "import sys, time\ntime.sleep(60)\n", encoding="utf-8")
            garbage = pathlib.Path(tmp) / "garbage.py"
            garbage.write_text("print('not json{{{')\n", encoding="utf-8")
            fx = pathlib.Path(tmp) / "f.pep"
            fx.write_text('say(int_text(1))\n', encoding="utf-8")
            m = write_manifest(tmp, [{"id": "t1", "file": "f.pep", "kind": "run",
                                      "expect": {"exit": 0, "stdout": "1\n"}}])
            proc = run_runner("--json", "--timeout", "3", manifest=m, pep=sleeper,
                                timeout=120)
            doc = json.loads(proc.stdout)
            self.assertEqual(doc["tests"][0]["status"], "timeout")
            self.assertNotEqual(proc.returncode, 0)
            m2 = write_manifest(tmp, [{"id": "g1", "file": "f.pep", "kind": "reject",
                                       "expect": {"code": "X"}}])
            proc2 = run_runner("--json", manifest=m2, pep=garbage)
            doc2 = json.loads(proc2.stdout)
            self.assertEqual(doc2["tests"][0]["status"], "infra_error")

    def test_filter_selects_subset(self):
        proc = run_runner("--json", "--filter", "reject/")
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["counts"]["pass"], 2)
        self.assertTrue(all(t["id"].startswith("reject/") for t in doc["tests"]))

    def test_list_lists_without_executing(self):
        proc = run_runner("--json", "--list")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads(proc.stdout)
        ids = [t["id"] for t in doc["tests"]]
        self.assertIn("pass/add", ids)
        self.assertIn("skip/native-differential", ids)
        for t in doc["tests"]:
            self.assertNotIn("status", t)  # listed, never executed
        proc2 = run_runner("--list", "--filter", "reject/")
        self.assertEqual(proc2.returncode, 0)
        self.assertIn("reject/type-mismatch", proc2.stdout)
        self.assertNotIn("pass/add", proc2.stdout)

    def test_skip_recorded_with_reason_never_executed(self):
        proc = run_runner("--json", "--filter", "skip/")
        doc = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0)  # skips do not fail the run
        self.assertEqual(doc["counts"]["skip"], 1)
        self.assertEqual(doc["tests"][0]["status"], "skip")
        self.assertIn("native", doc["tests"][0]["detail"])

    def test_check_kind_fixture_passes(self):
        proc = run_runner("--json", "--filter", "check/")
        doc = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(doc["counts"]["pass"], 1)
        self.assertEqual(doc["tests"][0]["id"], "check/record-shape")


    def test_evidence_artifacts_recorded_per_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            exp = pathlib.Path(tmp) / "exp"
            proc = run_runner("--json", "--filter", "pass/add",
                              "--evidence-dir", str(exp))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            doc = json.loads(proc.stdout)
            t = doc["tests"][0]
            self.assertIn("evidence", t)
            self.assertIn("stdout.txt", t["evidence"])
            self.assertIn("check.json", t["evidence"])
            for name, path in t["evidence"].items():
                self.assertTrue(pathlib.Path(path).is_file(), name)
            self.assertEqual(
                pathlib.Path(t["evidence"]["stdout.txt"]).read_text(encoding="utf-8"),
                t["stdout"])
            check_doc = json.loads(
                pathlib.Path(t["evidence"]["check.json"]).read_text(encoding="utf-8"))
            self.assertEqual(check_doc["status"], "valid")
            self.assertEqual(doc["evidence_root"], str(exp))


if __name__ == "__main__":
    unittest.main()
