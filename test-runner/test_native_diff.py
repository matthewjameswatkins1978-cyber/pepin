"""Adversarial tests for the native differential adapter (interpreter/clang/gcc).

Every case here exists to prove a differential can never be faked:

* a missing compiler is an infrastructure result, never a pass;
* clang and gcc disagreeing is a `divergence`, not a tolerant pass;
* a backend that suddenly supports a declared-unsupported fixture fails the
  declaration (and vice versa) instead of being silently ignored;
* a compiler rejecting the emitted C is a `compile_error`, not `unsupported`;
* a toolchain error is `infra_error`, never `unsupported`;
* an invalid program that a native backend *executes* is a failure;
* only the two leading `C23:`/`Executable:` build lines are stripped, so a
  program's own stderr is compared verbatim;
* timeouts and garbage output never pass.

Most cases drive a stub CLI through the real runner, so they need no real
compiler and stay deterministic. One case exercises the real toolchain when
clang and gcc are installed on this machine.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "test-runner" / "pep_test.py"
REAL_MANIFEST = ROOT / "test-runner" / "manifest.json"

STUB_TEMPLATE = '''import json
import sys
import time

SPEC = json.loads({spec!r})


def emit(block):
    if block.get("sleep"):
        time.sleep(block["sleep"])
    if block.get("stdout"):
        sys.stdout.write(block["stdout"])
    if block.get("stderr"):
        sys.stderr.write(block["stderr"])
    return block.get("exit", 0)


def main(argv):
    command = argv[0]
    if command == "run":
        return emit(SPEC.get("run", {{}}))
    if command == "run-c23":
        compiler = ""
        if "--compiler" in argv:
            compiler = argv[argv.index("--compiler") + 1]
        block = SPEC.get("gcc" if "gcc" in compiler.lower() else "clang", {{}})
        if block.get("no_metadata"):
            return emit(block)
        sys.stderr.write("C23: /tmp/generated.c\\n")
        sys.stderr.write("Executable: /tmp/generated.exe\\n")
        return emit(block)
    sys.stderr.write("stub: unknown command %s\\n" % command)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''

DEFAULT_RUN = {"stdout": "42\n", "exit": 0}
DEFAULT_NATIVE = {"stdout": "42\n", "exit": 0}


class NativeDifferentialTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def build(self, run=None, clang=None, gcc=None, expect=None, kind="native"):
        spec = {"run": run or dict(DEFAULT_RUN),
                "clang": clang or dict(DEFAULT_NATIVE),
                "gcc": gcc or dict(DEFAULT_NATIVE)}
        stub = self.tmp / "stub.py"
        stub.write_text(STUB_TEMPLATE.format(spec=json.dumps(spec)), encoding="utf-8")
        (self.tmp / "p.pep").write_text("fn main() -> Int { return 40 + 2 }\n",
                                        encoding="utf-8")
        for name in ("clang.exe", "gcc.exe"):
            (self.tmp / name).write_text("", encoding="utf-8")
        manifest = self.tmp / "m.json"
        manifest.write_text(json.dumps({
            "schemaVersion": 1,
            "fixtures": [{"id": "n/one", "file": "p.pep", "kind": kind,
                          "expect": expect if expect is not None else
                          {"exit": 0, "stdout": "42\n"}}],
        }), encoding="utf-8")
        return manifest, stub

    def run_native(self, manifest, stub, *args, backends="interpreter,clang,gcc",
                   clang=None, gcc=None, timeout=120):
        cmd = [sys.executable, str(RUNNER), "--manifest", str(manifest),
               "--pep", str(stub), "--backend", backends]
        if clang is not False:
            cmd += ["--compiler-clang", str(clang or (self.tmp / "clang.exe"))]
        if gcc is not False:
            cmd += ["--compiler-gcc", str(gcc or (self.tmp / "gcc.exe"))]
        cmd += [str(a) for a in args]
        return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)

    def status_of(self, proc):
        doc = json.loads(proc.stdout)
        return doc["tests"][0]["status"], doc["tests"][0], doc

    # -- agreement -------------------------------------------------------
    def test_three_way_agreement_passes(self):
        manifest, stub = self.build()
        proc = self.run_native(manifest, stub, "--json")
        status, test, doc = self.status_of(proc)
        self.assertEqual(status, "pass", test.get("detail"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(doc["backends"], ["interpreter", "clang", "gcc"])
        self.assertEqual([o["backend"] for o in test["observed"]],
                         ["interpreter", "clang", "gcc"])
        # Build chatter must be stripped from the compared stderr.
        for item in test["observed"]:
            if item["backend"] != "interpreter":
                self.assertEqual(item["stderr"], "")
                self.assertEqual(len(item["metadata"]), 2)

    # -- divergence ------------------------------------------------------
    def test_compiler_disagreement_is_divergence(self):
        manifest, stub = self.build(gcc={"stdout": "43\n", "exit": 0},
                                    expect={"exit": 0, "stdout": "42\n"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, doc = self.status_of(proc)
        self.assertIn(status, ("divergence", "fail"), test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotEqual(doc["counts"]["pass"], 1)

    def test_exit_code_disagreement_is_not_a_pass(self):
        manifest, stub = self.build(
            clang={"stdout": "42\n", "exit": 0},
            gcc={"stdout": "42\n", "exit": 3},
            expect={"exit": 0, "stdout": "42\n"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertNotEqual(status, "pass", test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)

    def test_interpreter_mismatch_fails_even_when_natives_agree(self):
        manifest, stub = self.build(run={"stdout": "41\n", "exit": 0})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("interpreter", test.get("detail", ""))

    def test_stdout_mismatch_on_every_backend_fails(self):
        manifest, stub = self.build(
            run={"stdout": "42\n", "exit": 0},
            clang={"stdout": "42\n", "exit": 0},
            gcc={"stdout": "42\n", "exit": 0},
            expect={"exit": 0, "stdout": "99\n"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))

    # -- unsupported declarations ---------------------------------------
    def test_declared_unsupported_is_not_a_pass(self):
        reason = "Pep C23 main function must return Int"
        unsupported = {"stderr": "Pep C23 unsupported: %s\n" % reason, "exit": 2}
        manifest, stub = self.build(run={"stdout": "hi\n", "exit": 0},
                                    clang=unsupported, gcc=unsupported,
                                    expect={"exit": 0, "stdout": "hi\n",
                                            "nativeUnsupported": "must return Int"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, doc = self.status_of(proc)
        self.assertEqual(status, "unsupported", test.get("detail"))
        self.assertEqual(doc["counts"]["unsupported"], 1)
        self.assertEqual(doc["counts"]["pass"], 0)
        self.assertEqual(proc.returncode, 0)

    def test_stale_unsupported_declaration_fails_when_backend_now_runs(self):
        unsupported = {"stderr": "Pep C23 unsupported: Pep C23 nope\n", "exit": 2}
        manifest, stub = self.build(
            run={"stdout": "42\n", "exit": 0},
            clang=unsupported, gcc=dict(DEFAULT_NATIVE),
            expect={"exit": 0, "stdout": "42\n", "nativeUnsupported": "nope"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("now ran it", test.get("detail", ""))
        self.assertNotEqual(proc.returncode, 0)

    def test_changed_unsupported_reason_fails(self):
        unsupported = {"stderr": "Pep C23 unsupported: something else entirely\n",
                       "exit": 2}
        manifest, stub = self.build(run={"stdout": "", "exit": 0},
                                    clang=unsupported, gcc=unsupported,
                                    expect={"exit": 0, "stdout": "",
                                            "nativeUnsupported": "must return Int"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("reason changed", test.get("detail", ""))

    def test_undeclared_unsupported_is_a_regression_failure(self):
        unsupported = {"stderr": "Pep C23 unsupported: unexpected\n", "exit": 2}
        manifest, stub = self.build(clang=unsupported, gcc=unsupported)
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("without a declaration", test.get("detail", ""))

    # -- infrastructure vs unsupported vs build error --------------------
    def test_missing_compiler_is_infra_error_never_a_pass(self):
        missing = self.tmp / "does-not-exist-clang.exe"
        manifest, stub = self.build()
        proc = self.run_native(manifest, stub, "--json", clang=missing)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("backend unavailable", proc.stdout + proc.stderr)
        self.assertNotIn("pass=", proc.stdout)

    def test_toolchain_error_prefix_is_infra_error(self):
        broken = {"stderr": "Pep C23 error: cannot invoke compiler\n", "exit": 2}
        manifest, stub = self.build(clang=broken, gcc=broken)
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "infra_error", test.get("detail"))

    def test_compiler_rejecting_emitted_c_is_compile_error(self):
        refused = {"stderr": "generated.c:12:5: error: expected ';'\n", "exit": 1}
        manifest, stub = self.build(clang=refused, gcc=refused)
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertIn(status, ("compile_error", "fail"), test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)

    def test_bare_exit_two_without_prefix_is_compile_error(self):
        refused = {"stderr": "cc1: fatal error: not C\n", "exit": 2}
        manifest, stub = self.build(clang=refused, gcc=refused)
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "compile_error", test.get("detail"))

    def test_native_timeout_never_passes(self):
        slow = {"stdout": "42\n", "exit": 0, "sleep": 30}
        manifest, stub = self.build(clang=slow, expect={"exit": 0, "stdout": "42\n"})
        proc = self.run_native(manifest, stub, "--json", "--timeout", "1")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "timeout", test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)

    # -- invalid programs -------------------------------------------------
    def test_reject_parity_passes_when_all_backends_reject(self):
        unsupported = {"stderr": "Pep C23 unsupported: requires a valid Pep checker report\n",
                       "exit": 2}
        manifest, stub = self.build(
            run={"stderr": "1:31: PEP_TYPE_MISMATCH: Expected Int but found Bool\n",
                 "exit": 1},
            clang=unsupported, gcc=unsupported,
            expect={"match": "reject", "diagnosticCode": "PEP_TYPE_MISMATCH"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "pass", test.get("detail"))

    def test_reject_parity_fails_when_a_backend_runs_the_invalid_program(self):
        manifest, stub = self.build(
            run={"stderr": "1:31: PEP_TYPE_MISMATCH: Expected Int but found Bool\n",
                 "exit": 1},
            clang=dict(DEFAULT_NATIVE), gcc=dict(DEFAULT_NATIVE),
            expect={"match": "reject", "diagnosticCode": "PEP_TYPE_MISMATCH"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("must never run", test.get("detail", ""))

    def test_diagnostic_mode_detects_a_different_runtime_code(self):
        manifest, stub = self.build(
            run={"stderr": "2:14: PEP_RUNTIME_DIVISION_BY_ZERO: Division by zero\n",
                 "exit": 1},
            clang={"stderr": "PEP_RUNTIME_OVERFLOW\n", "exit": 1},
            gcc={"stderr": "PEP_RUNTIME_OVERFLOW\n", "exit": 1},
            expect={"match": "diagnostic", "exit": 1,
                    "diagnosticCode": "PEP_RUNTIME_DIVISION_BY_ZERO"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertIn("PEP_RUNTIME_OVERFLOW", test.get("detail", ""))

    # -- selection and configuration -------------------------------------
    def test_unknown_backend_is_infra_error(self):
        manifest, stub = self.build()
        proc = self.run_native(manifest, stub, "--json", backends="interpreter,cobol")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown backend", proc.stdout + proc.stderr)

    def test_interpreter_only_run_excludes_native_fixtures(self):
        manifest, stub = self.build()
        proc = self.run_native(manifest, stub, "--json", backends="interpreter",
                              clang=False, gcc=False)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("no interpreter fixtures", proc.stdout + proc.stderr)

    def test_program_stderr_named_like_metadata_is_preserved(self):
        # Only the two leading build lines are metadata; later lines belong to
        # the program and must survive into the comparison.
        tricky = {"stderr": "C23: program says hello\n", "stdout": "42\n", "exit": 0}
        manifest, stub = self.build(clang=tricky, gcc=tricky)
        proc = self.run_native(manifest, stub, "--json")
        _status, test, _ = self.status_of(proc)
        clang = [o for o in test["observed"] if o["backend"] == "clang"][0]
        self.assertEqual(clang["stderr"], "C23: program says hello\n")
        self.assertEqual(len(clang["metadata"]), 2)


    # -- declaration validation ------------------------------------------
    def test_native_fixture_skip_never_executes(self):
        manifest, stub = self.build()
        manifest.write_text(json.dumps({
            "schemaVersion": 1,
            "fixtures": [{"id": "n/skipped", "file": "p.pep", "kind": "native",
                          "skip": "declared native gap",
                          "expect": {"exit": 0, "stdout": "42\n"}}],
        }), encoding="utf-8")
        proc = self.run_native(manifest, stub, "--json")
        doc = json.loads(proc.stdout)
        test = doc["tests"][0]
        self.assertEqual(test["status"], "skip", test.get("detail"))
        self.assertIn("declared native gap", test["detail"])
        self.assertNotIn("observed", test)  # nothing was executed
        self.assertEqual(proc.returncode, 0)

    def test_duplicate_native_ids_are_infra_error(self):
        manifest, stub = self.build()
        entry = {"id": "n/dup", "file": "p.pep", "kind": "native",
                 "expect": {"exit": 0, "stdout": "42\n"}}
        manifest.write_text(json.dumps({"schemaVersion": 1,
                                        "fixtures": [entry, dict(entry)]}),
                            encoding="utf-8")
        proc = self.run_native(manifest, stub, "--json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("duplicate fixture ids", proc.stdout + proc.stderr)

    def test_unknown_native_match_mode_is_infra_error(self):
        manifest, stub = self.build(expect={"match": "vibes", "stdout": "42\n"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "infra_error", test.get("detail"))
        self.assertEqual(proc.returncode, 2)

    def test_diagnostic_mode_without_code_is_infra_error(self):
        manifest, stub = self.build(expect={"match": "diagnostic", "exit": 0})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "infra_error", test.get("detail"))
        self.assertEqual(proc.returncode, 2)

    def test_conflicting_declarations_are_infra_error(self):
        manifest, stub = self.build(expect={"match": "reject",
                                            "diagnosticCode": "PEP_TYPE_MISMATCH",
                                            "nativeUnsupported": "anything"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "infra_error", test.get("detail"))
        self.assertIn("one outcome", test.get("detail", ""))

    def test_unsupported_marker_with_zero_exit_is_not_a_run(self):
        confused = {"stderr": "Pep C23 unsupported: somehow exit 0\n", "exit": 0}
        manifest, stub = self.build(clang=confused, gcc=confused,
                                    expect={"exit": 0, "stdout": "42\n"})
        proc = self.run_native(manifest, stub, "--json")
        status, test, doc = self.status_of(proc)
        self.assertNotEqual(status, "pass", test.get("detail"))
        self.assertEqual(doc["counts"]["pass"], 0)

    def test_interpreter_garbage_output_is_a_failure_not_a_pass(self):
        manifest, stub = self.build(run={"stderr": "crashed mid-run\n", "exit": 7})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)

    def test_native_fixture_without_expect_is_a_strict_expectation(self):
        # No expect block means "empty stdout, exit 0" — never "anything goes".
        manifest, stub = self.build(expect={})
        proc = self.run_native(manifest, stub, "--json")
        status, test, _ = self.status_of(proc)
        self.assertEqual(status, "fail", test.get("detail"))
        self.assertNotEqual(proc.returncode, 0)


@unittest.skipUnless(shutil.which("clang") and shutil.which("gcc"),
                     "clang and gcc are required for the real differential")
class RealToolchainDifferentialTests(unittest.TestCase):
    def test_real_manifest_differential_agrees(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--manifest", str(REAL_MANIFEST),
             "--backend", "interpreter,clang,gcc", "--json"],
            text=True, capture_output=True, timeout=1800)
        self.assertEqual(proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-2000:])
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["backends"], ["interpreter", "clang", "gcc"])
        self.assertEqual(doc["counts"]["fail"], 0)
        self.assertEqual(doc["counts"]["divergence"], 0)
        self.assertEqual(doc["counts"]["compile_error"], 0)
        self.assertEqual(doc["counts"]["infra_error"], 0)
        # The declared-unsupported subset must be recorded apart from passes.
        self.assertGreater(doc["counts"]["unsupported"], 0)
        native = [t for t in doc["tests"] if t["kind"] == "native"]
        self.assertTrue(native)
        for test in native:
            self.assertIn(test["status"], ("pass", "unsupported"))
            self.assertEqual(len(test["observed"]), 3)


if __name__ == "__main__":
    unittest.main()
