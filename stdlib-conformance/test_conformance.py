"""Adversarial tests for the standard-library conformance harness.

The harness is only useful if it cannot lie, so these tests pin:

* composition (the only way Pep can express a case today) is exact;
* a wrong expectation fails, so passing cases are evidence;
* a missing or unusable library is an infrastructure error (exit 2), not a pass;
* an empty, malformed or duplicate case table is refused, so no vacuous green;
* an unknown helper surfaces as a non-pass through the real runner;
* the real library, when present in this branch, satisfies the contract.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "stdlib-conformance" / "conformance.py"
PEP = ROOT / "pep.ps1"
CASES = ROOT / "stdlib-conformance" / "cases.json"

sys.path.insert(0, str(ROOT / "stdlib-conformance"))
import conformance  # noqa: E402

LIBRARY = (
    "fn lib_double(x: Int) -> Int { return x + x }\n"
    "fn lib_is_zero(x: Int) -> Bool { if x == 0 { return true } else { return false } }\n"
)


def run_harness(*args, timeout=900):
    cmd = [sys.executable, str(HARNESS), "--pep", str(PEP)] + [str(a) for a in args]
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


class ComposeTests(unittest.TestCase):
    def test_int_case_is_wrapped_in_int_text(self):
        source = conformance.compose(LIBRARY,
                                     {"id": "x", "expr": "lib_double(21)",
                                      "result": "Int", "expect": "42"})
        self.assertTrue(source.startswith("fn lib_double"))
        self.assertTrue(source.endswith("say(int_text(lib_double(21)))\n"))

    def test_bool_case_branches_because_bool_text_does_not_exist(self):
        source = conformance.compose(LIBRARY,
                                     {"id": "x", "expr": "lib_is_zero(0)",
                                      "result": "Bool", "expect": "true"})
        self.assertTrue(source.endswith(
            'say(if lib_is_zero(0) { "true" } else { "false" })\n'))
        self.assertNotIn("bool_text", source)

    def test_missing_trailing_newline_does_not_merge_statements(self):
        source = conformance.compose("fn f() -> Int { return 1 }",
                                     {"id": "x", "expr": "f()", "result": "Int",
                                      "expect": "1"})
        self.assertIn("}\nsay(", source)


class DependencyTests(unittest.TestCase):
    COMMENT_LIBRARY = (
        "fn alpha(x: Int) -> Int { return x + 1 }\n"
        "// this comment mentions beta( and must not create a dependency\n"
        "fn beta(x: Int) -> Int { return alpha(x) }\n"
    )

    def test_dependency_scan_ignores_comments(self):
        names = conformance.reachable_functions(self.COMMENT_LIBRARY, "alpha(1)")
        self.assertEqual(names, ["alpha"])

    def test_transitive_dependencies_follow_calls(self):
        names = conformance.reachable_functions(self.COMMENT_LIBRARY, "beta(1)")
        self.assertEqual(names, ["alpha", "beta"])

    def test_pruning_keeps_library_order(self):
        source = conformance.compose(self.COMMENT_LIBRARY,
                                     {"id": "x", "expr": "beta(1)",
                                      "result": "Int", "expect": "2"})
        self.assertLess(source.index("fn alpha"), source.index("fn beta"))

    def test_native_shape_carries_main_and_top_level_call(self):
        source = conformance.compose(self.COMMENT_LIBRARY,
                                     {"id": "x", "expr": "alpha(1)",
                                      "result": "Int", "expect": "2"},
                                     native=True)
        self.assertIn("fn main() -> Int { return alpha(1) }", source)
        self.assertTrue(source.endswith("say(int_text(alpha(1)))\n"))


class CaseTableTests(unittest.TestCase):
    def test_native_declarations_reject_overlap(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.native_declarations(
                {"native": {"supported": ["f"],
                            "unsupported": {"f": "reason"}}})

    def test_native_declarations_require_reasons(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.native_declarations(
                {"native": {"unsupported": {"f": "  "}}})

    def test_real_table_declares_native_boundary(self):
        supported, unsupported = conformance.native_declarations(
            conformance.load_cases(INTMATH_CASES))
        self.assertIn("int_abs", supported)
        self.assertIn("int_sign", unsupported)
        self.assertEqual(set(supported) & set(unsupported), set())
    def test_empty_table_is_refused(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.validate_cases({"cases": []})

    def test_duplicate_ids_are_refused(self):
        case = {"id": "dup", "expr": "f()", "result": "Int", "expect": "1"}
        with self.assertRaises(conformance.HarnessError):
            conformance.validate_cases({"cases": [case, dict(case)]})

    def test_unknown_result_kind_is_refused(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.validate_cases({"cases": [
                {"id": "x", "expr": "f()", "result": "Str", "expect": "1"}]})

    def test_bool_expect_must_be_true_or_false(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.validate_cases({"cases": [
                {"id": "x", "expr": "f()", "result": "Bool", "expect": "1"}]})

    def test_empty_expr_is_refused(self):
        with self.assertRaises(conformance.HarnessError):
            conformance.validate_cases({"cases": [
                {"id": "x", "expr": "  ", "result": "Int", "expect": "1"}]})

    def test_real_case_table_is_valid(self):
        cases = conformance.validate_cases(conformance.load_cases(CASES))
        self.assertGreater(len(cases), 20)
        ids = [c["id"] for c in cases]
        self.assertEqual(len(ids), len(set(ids)))


class EndToEndHarnessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        (self.tmp / "lib.pep").write_text(LIBRARY, encoding="utf-8", newline="\n")

    def tearDown(self):
        self._tmp.cleanup()

    def write_cases(self, cases):
        path = self.tmp / "cases.json"
        path.write_text(json.dumps({"schemaVersion": 1, "cases": cases}),
                        encoding="utf-8")
        return path

    def run_with(self, cases, *args):
        return run_harness("--repo", str(self.tmp), "--library", "lib.pep",
                           "--cases", str(self.write_cases(cases)),
                           "--out", str(self.tmp / "out"), *args)

    def test_correct_expectations_pass(self):
        proc = self.run_with([
            {"id": "double", "expr": "lib_double(21)", "result": "Int", "expect": "42"},
            {"id": "zero", "expr": "lib_is_zero(0)", "result": "Bool", "expect": "true"},
            {"id": "nonzero", "expr": "lib_is_zero(5)", "result": "Bool",
             "expect": "false"},
        ], "--json")
        self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-1000:])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["counts"]["pass"], 3)
        self.assertEqual(doc["counts"]["fail"], 0)

    def test_wrong_expectation_fails(self):
        proc = self.run_with([
            {"id": "double", "expr": "lib_double(21)", "result": "Int", "expect": "43"},
        ], "--json")
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["counts"]["fail"], 1)
        self.assertNotEqual(proc.returncode, 0)

    def test_unknown_helper_never_passes(self):
        proc = self.run_with([
            {"id": "ghost", "expr": "lib_missing(1)", "result": "Int", "expect": "1"},
        ], "--json")
        doc = json.loads(proc.stdout)
        status = doc["tests"][0]["status"]
        self.assertIn(status, ("compile_error", "fail", "infra_error"))
        self.assertEqual(doc["counts"]["pass"], 0)
        self.assertNotEqual(proc.returncode, 0)

    def test_manifest_records_library_provenance(self):
        proc = self.run_with([
            {"id": "double", "expr": "lib_double(21)", "result": "Int", "expect": "42"},
        ], "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr[-800:])
        manifest = json.loads((self.tmp / "out" / "manifest.json").read_text())
        library = manifest["library"]
        self.assertEqual(library["source"], str(self.tmp / "lib.pep"))
        self.assertTrue(library["sha256"].startswith("sha256:"))
        self.assertEqual(library["cases"], 1)

    def test_missing_library_revision_is_infra_error(self):
        proc = run_harness("--repo", str(self.tmp), "--library", "lib.pep",
                           "--library-rev", "0000000000000000000000000000000000000000",
                           "--out", str(self.tmp / "out2"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CONFORMANCE-INFRA-ERROR", proc.stderr)
        self.assertNotIn("pass=", proc.stdout)

    def test_missing_working_tree_library_is_infra_error(self):
        proc = run_harness("--repo", str(self.tmp), "--library", "no-such-lib.pep",
                           "--out", str(self.tmp / "out3"))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("library not found", proc.stderr)

    def test_empty_table_is_infra_error_not_green(self):
        proc = self.run_with([])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("defines no cases", proc.stderr)
        self.assertNotIn("pass=", proc.stdout)

    def test_native_without_declarations_is_infra_error(self):
        # --native must never silently fall back to interpreter-only results.
        proc = self.run_with([
            {"id": "double", "expr": "lib_double(21)", "result": "Int", "expect": "42"},
        ], "--native")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--native needs native declarations", proc.stderr)
        self.assertNotIn("pass=", proc.stdout)


INTMATH_CASES = ROOT / "stdlib-conformance" / "cases-intmath.json"


class RealLibraryConformanceTests(unittest.TestCase):
    def test_native_column_executes_supported_helpers(self):
        # Real clang and gcc must actually run the declared-supported helpers.
        proc = run_harness("--library", "stdlib/intmath.pep",
                           "--cases", str(INTMATH_CASES), "--native",
                           "--filter", "int_abs/", "--json", timeout=1800)
        self.assertEqual(proc.returncode, 0,
                         proc.stdout[-2500:] + proc.stderr[-1500:])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["backends"], ["interpreter", "clang", "gcc"])
        self.assertGreaterEqual(doc["counts"]["pass"], 3)
        for test in doc["tests"]:
            self.assertEqual(test["kind"], "native")
            self.assertEqual(len(test["observed"]), 3)

    def test_intmath_module_satisfies_its_contract(self):
        # stdlib/intmath.pep is owned by this lane, so this always runs.
        proc = run_harness("--library", "stdlib/intmath.pep",
                           "--cases", str(INTMATH_CASES), "--json", timeout=1800)
        self.assertEqual(proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-1500:])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["counts"]["fail"], 0)
        self.assertEqual(doc["counts"]["infra_error"], 0)
        self.assertGreaterEqual(doc["counts"]["pass"], 35)

    def test_collections_library_satisfies_contract_when_present(self):
        library = ROOT / "stdlib" / "collections.pep"
        if not library.is_file():
            self.skipTest("stdlib/collections.pep is not in this branch yet "
                          "(Agent 2 owns it); run with --library-rev instead")
        proc = run_harness("--json", timeout=1800)
        self.assertEqual(proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-1500:])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["counts"]["fail"], 0)
        self.assertGreater(doc["counts"]["pass"], 20)


if __name__ == "__main__":
    unittest.main()
