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
        self.assertEqual(doc["counts"]["pass"], 12)
        self.assertEqual(doc["counts"]["skip"], 0)
        self.assertEqual(doc["counts"]["fail"], 0)
        for t in doc["tests"]:
            self.assertIn("source_sha256", t)
        self.assertTrue(doc["repoRevision"])
        self.assertEqual(doc["backend"], "interpreter")
        # Native fixtures are declared but stay out of an interpreter-only run.
        self.assertEqual(doc["backends"], ["interpreter"])
        self.assertFalse([t for t in doc["tests"] if t["kind"] == "native"])

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
        self.assertEqual(doc["counts"]["pass"], 4)
        self.assertTrue(all(t["id"].startswith("reject/") for t in doc["tests"]))

    def test_v8_gate_statuses_all_distinct_in_counts(self):
        # Road 2 V8 gate: pass/fail/compile/runtime/timeout/policy/infra/skip stay
        # distinct. policy_denied is reserved (no current CLI surface triggers it)
        # but present in counts and schema so a future enforcing backend plugs in.
        proc = run_runner("--json", "--filter", "pass/add")
        doc = json.loads(proc.stdout)
        for key in ("pass", "fail", "compile_error", "runtime_error",
                    "timeout", "infra_error", "skip", "policy_denied"):
            self.assertIn(key, doc["counts"], key)
        self.assertEqual(doc["counts"]["policy_denied"], 0)

    def test_empty_selection_fails_loudly(self):
        proc = run_runner("--json", "--filter", "no-such-fixture-xyz")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no fixtures match", proc.stdout + proc.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            m = write_manifest(tmp, [])
            proc2 = run_runner("--json", manifest=m)
            self.assertEqual(proc2.returncode, 2)

    def test_list_lists_without_executing(self):
        proc = run_runner("--json", "--list")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads(proc.stdout)
        ids = [t["id"] for t in doc["tests"]]
        self.assertIn("pass/add", ids)
        self.assertIn("native/arith-return", ids)
        for t in doc["tests"]:
            self.assertNotIn("status", t)  # listed, never executed
        proc2 = run_runner("--list", "--filter", "reject/")
        self.assertEqual(proc2.returncode, 0)
        self.assertIn("reject/type-mismatch", proc2.stdout)
        self.assertNotIn("pass/add", proc2.stdout)

    def test_skip_recorded_with_reason_never_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "s.pep").write_text("say(int_text(1))\n",
                                                     encoding="utf-8")
            m = write_manifest(tmp, [{"id": "skip/known-gap", "file": "s.pep",
                                      "kind": "run",
                                      "skip": "declared gap, not executed",
                                      "expect": {"exit": 0, "stdout": "1\n"}}])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            self.assertEqual(proc.returncode, 0)  # skips do not fail the run
            self.assertEqual(doc["counts"]["skip"], 1)
            self.assertEqual(doc["tests"][0]["status"], "skip")
            self.assertIn("declared gap", doc["tests"][0]["detail"])
            self.assertNotIn("exit", doc["tests"][0])  # never executed
            self.assertNotIn("stdout", doc["tests"][0])

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


    def test_output_match_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "f.pep"
            f.write_text('say("hello 42 world")\n', encoding="utf-8")
            m = write_manifest(tmp, [
                {"id": "c1", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "42", "match": "contains"}},
                {"id": "c2", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "nope", "match": "contains"}},
                {"id": "r1", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "hello \\d+ world", "match": "regex"}},
                {"id": "r2", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "hello \\d+$", "match": "regex"}},
                {"id": "b1", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "([", "match": "regex"}},
                {"id": "u1", "file": "f.pep", "kind": "run",
                 "expect": {"exit": 0, "stdout": "hello", "match": "fuzzy"}},
            ])
            proc = run_runner("--json", manifest=m)
            doc = json.loads(proc.stdout)
            by_id = {t["id"]: t for t in doc["tests"]}
            self.assertEqual(by_id["c1"]["status"], "pass")
            self.assertEqual(by_id["c2"]["status"], "fail")
            self.assertEqual(by_id["r1"]["status"], "pass")
            self.assertEqual(by_id["r2"]["status"], "fail")
            self.assertEqual(by_id["b1"]["status"], "infra_error")
            self.assertEqual(by_id["u1"]["status"], "infra_error")
            self.assertNotEqual(proc.returncode, 0)
            # contains/regex without an explicit expected string must not pass vacuously.
            m2 = write_manifest(tmp, [{"id": "v1", "file": "f.pep", "kind": "run",
                                       "expect": {"exit": 0, "match": "contains"}}])
            proc2 = run_runner("--json", manifest=m2)
            doc2 = json.loads(proc2.stdout)
            self.assertEqual(doc2["tests"][0]["status"], "infra_error")


    def check_schema(self, schema, doc, path="root"):
        """Minimal JSON Schema validator for the constructs results-schema.json uses."""
        self.assertIsInstance(doc, dict, path)
        if schema.get("type") == "object" or "properties" in schema or "required" in schema:
            self.assertIsInstance(doc, dict, path)
            for key in schema.get("required", []):
                self.assertIn(key, doc, "%s missing %s" % (path, key))
            for key, subschema in schema.get("properties", {}).items():
                if key in doc:
                    self.check_value(subschema, doc[key], "%s.%s" % (path, key))
        return True

    def check_value(self, schema, value, path):
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            schema = self.DEFS[name]
        expected = schema.get("type")
        if expected:
            kinds = expected if isinstance(expected, list) else [expected]
            ok = False
            for kind in kinds:
                if kind == "object" and isinstance(value, dict):
                    ok = True
                elif kind == "array" and isinstance(value, list):
                    ok = True
                elif kind == "string" and isinstance(value, str):
                    ok = True
                elif kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
                    ok = True
                elif kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
                    ok = True
                elif kind == "boolean" and isinstance(value, bool):
                    ok = True
                elif kind == "null" and value is None:
                    ok = True
            self.assertTrue(ok, "%s: %r is not %s" % (path, value, kinds))
        if "const" in schema:
            self.assertEqual(value, schema["const"], path)
        if "enum" in schema:
            self.assertIn(value, schema["enum"], path)
        if "pattern" in schema and isinstance(value, str):
            import re as _re
            self.assertTrue(_re.search(schema["pattern"], value), path)
        if "minimum" in schema and isinstance(value, (int, float)):
            self.assertGreaterEqual(value, schema["minimum"], path)
        if isinstance(value, dict):
            for key in schema.get("required", []):
                self.assertIn(key, value, "%s missing %s" % (path, key))
            props = schema.get("properties", {})
            for key, sub in props.items():
                if key in value:
                    self.check_value(sub, value[key], "%s.%s" % (path, key))
            if isinstance(schema.get("additionalProperties"), dict):
                for key, item in value.items():
                    if key not in props:
                        self.check_value(schema["additionalProperties"], item,
                                         "%s.%s" % (path, key))
        if isinstance(value, list) and "items" in schema:
            for i, item in enumerate(value):
                self.check_value(schema["items"], item, "%s[%d]" % (path, i))

    DEFS = {}

    def test_results_conform_to_published_schema(self):
        import pathlib as _pathlib
        schema_path = ROOT / "test-runner" / "results-schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        type(self).DEFS = schema.get("$defs", {})
        proc = run_runner("--json", "--filter", "pass/add")
        doc = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.check_schema(schema, doc)
        # --list output validates its own entry shape.
        proc2 = run_runner("--json", "--list")
        list_doc = json.loads(proc2.stdout)
        for entry in list_doc["tests"]:
            self.check_value(type(self).DEFS["listEntry"], entry, "list.tests[]")
        # The checker is not vacuous: tampered docs must fail.
        bad = json.loads(json.dumps(doc))
        bad["tests"][0]["status"] = "PROVEN"
        with self.assertRaises(AssertionError):
            self.check_schema(schema, bad)


    def test_manifest_validation_rejects_bad_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp) / "f.pep"
            f.write_text("say(1)\n", encoding="utf-8")
            good = {"id": "x", "file": "f.pep", "kind": "run",
                    "expect": {"exit": 0, "stdout": "1\n"}}
            # Duplicate fixture ids are ambiguous: refuse, do not run.
            m = write_manifest(tmp, [dict(good), dict(good)])
            proc = run_runner("--json", manifest=m)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("duplicate", proc.stdout.lower())
            # Non-positive or non-numeric timeouts are usage errors.
            m2 = write_manifest(tmp, [dict(good)])
            for extra in (["--timeout", "0"], ["--timeout", "-3"]):
                proc = run_runner("--json", manifest=m2, *extra)
                self.assertEqual(proc.returncode, 2, extra)
                self.assertIn("timeout", proc.stdout.lower())
            m3 = pathlib.Path(tmp) / "m3.json"
            m3.write_text(json.dumps({"schemaVersion": 1, "fixtures": [dict(good)],
                                      "limits": {"timeoutSeconds": -1}}), encoding="utf-8")
            proc = run_runner("--json", manifest=m3)
            self.assertEqual(proc.returncode, 2)
            bad_fx = dict(good, id="y", timeoutSeconds="soon")
            m4 = write_manifest(tmp, [bad_fx])
            proc = run_runner("--json", manifest=m4)
            doc = json.loads(proc.stdout)
            self.assertEqual(doc["tests"][0]["status"], "infra_error")


if __name__ == "__main__":
    unittest.main()
