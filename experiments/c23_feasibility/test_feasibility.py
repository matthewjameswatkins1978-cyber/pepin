import argparse
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
MANIFEST = json.loads((ROOT / "toolchain_paths.json").read_text(encoding="utf-8"))
EXPECTED_SHARED = [42, 42, 42, 49, 120, 5050]


def run(command, cwd=REPO, env=None):
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def resolve_compiler(name, environ=None, path_lookup=shutil.which, path_exists=Path.exists, known=None):
    environ = os.environ if environ is None else environ
    override_name = "PEP_C23_CLANG" if name == "clang" else "PEP_C23_GCC"
    override = environ.get(override_name)
    if override and path_exists(Path(override)):
        return str(Path(override))
    discovered = path_lookup(name)
    if discovered:
        return discovered
    for candidate in (MANIFEST if known is None else known).get(name, []):
        if path_exists(Path(candidate)):
            return str(Path(candidate))
    return None


def build_with(name, probe=False, env=None, sanitize=False):
    args = ["pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"), "-Compiler", name]
    if probe:
        args.append("-Probe")
    if sanitize:
        args.append("-Sanitize")
    return run(args, env=env)


def executable(name, probe=False, sanitize=False):
    stem = "pep_c23_language_probe" if probe else "pep_c23_probe"
    path = REPO / "_build" / "c23-feasibility" / name
    if sanitize:
        path = path / "sanitize"
    return path / f"{stem}.exe"


class CorpusPolicyTests(unittest.TestCase):
    def test_strict_c23_only(self):
        build = (ROOT / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("-std=c23", build)
        self.assertNotIn("gnu23", build)
        self.assertNotIn("c11", build.lower())

    def test_runtime_isolated(self):
        for path in ROOT.glob("*.c"):
            self.assertNotIn("pep_ocaml", path.read_text(encoding="utf-8"))
        self.assertFalse((REPO / "runtime" / "pep_runtime.c").samefile(ROOT / "c23_runtime.c"))


class DiscoveryMatrixTests(unittest.TestCase):
    def test_both_compilers_available(self):
        files = {"clang.exe", "gcc.exe"}
        known = {"clang": ["clang.exe"], "gcc": ["gcc.exe"]}
        exists = lambda path: path.name in files
        for name in ("clang", "gcc"):
            self.assertEqual(resolve_compiler(name, path_lookup=lambda _: None, path_exists=exists, known=known), f"{name}.exe")

    def test_only_clang_available(self):
        known = {"clang": ["clang.exe"], "gcc": ["gcc.exe"]}
        exists = lambda path: path.name == "clang.exe"
        self.assertEqual(resolve_compiler("clang", path_lookup=lambda _: None, path_exists=exists, known=known), "clang.exe")
        self.assertIsNone(resolve_compiler("gcc", path_lookup=lambda _: None, path_exists=exists, known=known))

    def test_explicit_override_wins(self):
        known = {"clang": ["known-clang.exe"]}
        exists = lambda path: path.name in {"override-clang.exe", "known-clang.exe"}
        env = {"PEP_C23_CLANG": "override-clang.exe"}
        self.assertEqual(resolve_compiler("clang", environ=env, path_lookup=lambda _: "path-clang", path_exists=exists, known=known), "override-clang.exe")

    def test_path_wins_before_known_locations(self):
        known = {"clang": ["known-clang.exe"]}
        self.assertEqual(resolve_compiler("clang", environ={}, path_lookup=lambda _: "path-clang", path_exists=lambda _: True, known=known), "path-clang")

    def test_neither_available(self):
        self.assertIsNone(resolve_compiler("clang", environ={}, path_lookup=lambda _: None, path_exists=lambda _: False, known={"clang": []}))

    def test_actual_driver_discovers_installed_compilers(self):
        for name in ("clang", "gcc"):
            self.assertIsNotNone(resolve_compiler(name), name)


class InterpreterOracleTests(unittest.TestCase):
    def assert_pep_output(self, source, expected):
        result = run(["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"), "run", str(REPO / source)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace("\r\n", "\n"), expected)

    def test_existing_pinned_examples(self):
        self.assert_pep_output("examples/hello.pep", "Hello, Pep!\n")
        self.assert_pep_output("examples/point_sum.pep", "42\n")
        self.assert_pep_output("examples/recursive_expr.pep", "42\n")
        self.assert_pep_output(
            "examples/a6_collections_control.pep",
            "42\n0\n1\n17\n22\n10\n0\n1\n42\n",
        )

    def test_shared_semantics_fixture(self):
        result = run(["pwsh", "-NoProfile", "-File", str(REPO / "pep.ps1"), "run", str(ROOT / "shared_semantics.pep")])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.replace("\r\n", "\n"), "\n".join(str(value) for value in EXPECTED_SHARED) + "\n")


class NativeProofTests(unittest.TestCase):
    def test_native_proof_when_compilers_exist(self):
        statuses = {}
        for name in ("clang", "gcc"):
            build = build_with(name, probe=True)
            if build.returncode == 2 and f"UNAVAILABLE|{name}" in build.stdout:
                statuses[name] = "unavailable"
                continue
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            statuses[name] = "available"
            feature = run([str(executable(name, probe=True))])
            self.assertEqual(feature.returncode, 0, feature.stdout + feature.stderr)
            runtime_build = build_with(name)
            self.assertEqual(runtime_build.returncode, 0, runtime_build.stdout + runtime_build.stderr)
            proof = run([str(executable(name))])
            self.assertEqual(proof.returncode, 0, proof.stdout + proof.stderr)
            self.assertIn("SUMMARY|failures=0", proof.stdout)
            observations = {}
            for line in proof.stdout.splitlines():
                if line.startswith("OBS|"):
                    _, key, value = line.split("|", 2)
                    observations[key] = value
            expected = {
                "checked_add_value_result": "42",
                "record_field_sum_result": "42",
                "recursive_union_match_result": "42",
                "list_sum_original_result": "42",
                "list_sum_extended_result": "49",
                "recursive_factorial_result": "120",
                "while_for_sum_result": "5050",
            }
            self.assertEqual({key: observations.get(key) for key in expected}, expected)
        if all(status == "unavailable" for status in statuses.values()):
            self.skipTest("strict C23 compilers are not installed on this host")
        self.assertEqual(statuses, {"clang": "available", "gcc": "available"})

    def test_compilation_failure_is_not_unavailable(self):
        with tempfile.TemporaryDirectory(dir=REPO / "_build") as temp:
            fake = Path(temp) / "fake-compiler.cmd"
            fake.write_text("@echo fake compiler\r\n@exit /b 23\r\n", encoding="utf-8")
            env = os.environ.copy()
            env["PEP_C23_CLANG"] = str(fake)
            result = build_with("clang", probe=True, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotEqual(result.returncode, 2)
            self.assertNotIn("UNAVAILABLE|clang", result.stdout)

    def test_executable_failure_is_nonzero(self):
        with tempfile.TemporaryDirectory(dir=REPO / "_build") as temp:
            fake = Path(temp) / "failing.ps1"
            fake.write_text("exit 7\n", encoding="utf-8")
            result = run(["pwsh", "-NoProfile", "-File", str(fake)])
            self.assertEqual(result.returncode, 7)

    def test_machine_readable_interpreter_comparison(self):
        result = run(["python", str(ROOT / "compare_semantics.py")])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["equal"])
        self.assertEqual([item["compiler"] for item in report["comparisons"]], ["clang", "gcc"])
        self.assertTrue(all(row["equal"] for item in report["comparisons"] for row in item["rows"]))

    def test_clang_address_sanitizer_proof(self):
        result = build_with("clang", sanitize=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        llvm_runtime = Path(r"C:\Users\Matmus\scoop\apps\llvm\current\lib\clang\23\lib\windows")
        env = os.environ.copy()
        env["PATH"] = str(llvm_runtime) + os.pathsep + env.get("PATH", "")
        proof = run([str(executable("clang", sanitize=True))], env=env)
        self.assertEqual(proof.returncode, 0, proof.stdout + proof.stderr)
        self.assertIn("SUMMARY|failures=0", proof.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", action="store_true")
    parser.parse_known_args()
    unittest.main(argv=["test_feasibility.py", "-v"])
