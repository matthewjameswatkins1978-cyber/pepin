import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
MANIFEST = json.loads((ROOT / "toolchain_paths.json").read_text(encoding="utf-8"))
EXPECTED_SHARED = [42, 42, 42, 49, 120, 5050]


def run(command, cwd=REPO, env=None):
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def expand_candidate(candidate, environ=None):
    environ = os.environ if environ is None else environ
    expanded = candidate
    for name in re.findall(r"\$\{([^}]+)\}", candidate):
        if name not in environ:
            return None
        expanded = expanded.replace("${" + name + "}", environ[name])
    return os.path.expandvars(expanded)


def resolve_compiler(name, environ=None, path_lookup=shutil.which, path_exists=Path.exists, known=None):
    environ = os.environ if environ is None else environ
    override_name = "PEP_C23_CLANG" if name == "clang" else "PEP_C23_GCC"
    override = environ.get(override_name)
    if override and path_exists(Path(override)):
        return str(Path(override))
    discovered = path_lookup(name)
    if discovered:
        return discovered
    for raw_candidate in (MANIFEST if known is None else known).get(name, []):
        candidate = expand_candidate(raw_candidate, environ)
        if candidate and path_exists(Path(candidate)):
            return str(Path(candidate))
    return None


def asan_runtime_dir(compiler):
    result = run([compiler, "--print-resource-dir"])
    if result.returncode == 0 and result.stdout.strip():
        candidate = Path(result.stdout.strip()) / "lib" / "windows"
        if (candidate / "clang_rt.asan_dynamic-x86_64.dll").exists():
            return candidate
    return None


def build_with(name, probe=False, env=None, sanitize=False, benchmark=False):
    args = ["pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"), "-Compiler", name]
    if probe:
        args.append("-Probe")
    if sanitize:
        args.append("-Sanitize")
    if benchmark:
        args.append("-Benchmark")
    return run(args, env=env)


def executable(name, probe=False, sanitize=False):
    stem = "pep_c23_language_probe" if probe else "pep_c23_probe"
    path = REPO / "_build" / "c23-feasibility" / name
    if sanitize:
        path = path / "sanitize"
    return path / f"{stem}.exe"


def benchmark_executable(name):
    return REPO / "_build" / "c23-feasibility" / name / "benchmark" / "pep_c23_benchmark.exe"


def fixture_executable(name):
    return REPO / "_build" / "c23-feasibility" / name / "fixtures" / "pep_c23_abi_fixture.exe"


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

    def test_toolchain_manifest_has_no_machine_home(self):
        manifest = (ROOT / "toolchain_paths.json").read_text(encoding="utf-8")
        self.assertNotIn("C:\\Users\\", manifest)


class FeatureSupportTests(unittest.TestCase):
    def test_named_nullptr_typedef_support_is_explicit(self):
        source = ROOT / "c23_named_nullptr_probe.c"
        for name in ("clang", "gcc"):
            compiler = resolve_compiler(name)
            self.assertIsNotNone(compiler, name)
            result = run([compiler, "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fsyntax-only", str(source)])
            if name == "clang":
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("nullptr_t", result.stderr)


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


class BenchmarkTests(unittest.TestCase):
    def test_clang_benchmark_harness_smoke(self):
        result = run(["python", str(ROOT / "benchmark_runtime.py"), "--compiler", "clang", "--trials", "2"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], 2)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(len(report["compilers"]), 1)
        self.assertEqual(len(report["compilers"][0]["rows"]), 21)
        self.assertTrue(all(row["validation"] == "passed" for row in report["compilers"][0]["rows"]))
        self.assertTrue(all(row["clock"] == "qpc" for row in report["compilers"][0]["rows"]))
        self.assertTrue(all(row["warmup_checksum"] == row["expected_checksum"] for row in report["compilers"][0]["rows"]))
        self.assertTrue(all(row["observed_checksums"] == [row["expected_checksum"]] * 2 for row in report["compilers"][0]["rows"]))

    def test_benchmark_oracle_negative_controls(self):
        import benchmark_runtime

        expected = benchmark_runtime.expected_case("list", 8, 100)
        valid = {
            **expected,
            "bytes": 0,
            "reserved": 0,
            "elapsed_ns": 1,
            "clock": "qpc",
        }

        for phase, trial in (("warmup", None), ("trial", 1), ("trial", 2)):
            with self.subTest(control=f"wrong {phase} checksum"):
                corrupted = {**valid, "checksum": valid["checksum"] + 1}
                with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                    benchmark_runtime.validate_record(corrupted, expected, "clang", phase, trial)

        with self.subTest(control="missing checksum"):
            missing = {key: value for key, value in valid.items() if key != "checksum"}
            with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                benchmark_runtime.validate_record(missing, expected, "clang", "trial", 1)

        with self.subTest(control="wrong operation count"):
            wrong_operations = {**valid, "operations": valid["operations"] + 1}
            with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                benchmark_runtime.validate_record(wrong_operations, expected, "clang", "trial", 1)

        with self.subTest(control="malformed output"):
            malformed = subprocess.CompletedProcess([], 0, "BENCH|case=list|bad\n", "")
            with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                benchmark_runtime.parse_record(malformed, {"compiler": "clang", "case": "list"})

        with self.subTest(control="unexpected process exit"):
            failed = subprocess.CompletedProcess([], 7, "", "synthetic failure")
            with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                benchmark_runtime.parse_record(failed, {"compiler": "clang", "case": "list"})

        def row(checksums):
            return {"case": "list", "size": 8, "iterations": 100, "observed_checksums": checksums}

        with self.subTest(control="compiler disagreement"):
            reports = [
                {"compiler": "clang", "rows": [row([expected["checksum"], expected["checksum"]])]},
                {"compiler": "gcc", "rows": [row([expected["checksum"] + 1, expected["checksum"] + 1])]},
            ]
            with self.assertRaises(benchmark_runtime.BenchmarkFailure):
                benchmark_runtime.validate_cross_compiler(reports)

    def test_benchmark_process_timeout_is_failure(self):
        import benchmark_runtime

        with self.assertRaises(benchmark_runtime.BenchmarkFailure):
            benchmark_runtime.timed_run([sys.executable, "-c", "import time; time.sleep(1)"], timeout_seconds=0.05)


class NativeProofTests(unittest.TestCase):
    def test_separate_translation_unit_abi_fixtures(self):
        observations = {}
        for name in ("clang", "gcc"):
            build = run([
                "pwsh", "-NoProfile", "-File", str(ROOT / "build.ps1"),
                "-Compiler", name, "-Fixtures",
            ])
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            commands = [line for line in build.stdout.splitlines() if line.startswith("COMMAND|")]
            self.assertEqual(len(commands), 4)
            self.assertEqual(sum(" -c " in line for line in commands), 3)
            proof = run([str(fixture_executable(name))])
            self.assertEqual(proof.returncode, 0, proof.stdout + proof.stderr)
            lines = proof.stdout.splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].startswith("ABI|compiler="))
            self.assertTrue(lines[1].startswith("LAYOUT|"))
            self.assertTrue(lines[2].startswith("ERRORS|"))
            parsed = {}
            for line in lines:
                fields = line.split("|")
                parsed[fields[0]] = dict(field.split("=", 1) for field in fields[1:])
            self.assertEqual(parsed["ABI"]["status"], "ok")
            self.assertEqual(parsed["ABI"]["point_sum"], "42")
            self.assertEqual(parsed["ABI"]["tree_sum"], "42")
            self.assertEqual(parsed["ABI"]["list_sum"], "49")
            self.assertEqual(parsed["ABI"]["utf8_len"], "3")
            self.assertEqual(parsed["ERRORS"], {
                "overflow": "overflow",
                "invalid_tag": "invalid_variant",
                "owner_mismatch": "range",
                "owner_recovery": "ok",
            })
            layout = parsed["LAYOUT"]
            self.assertEqual(layout["point_y_offset"], "8")
            self.assertGreaterEqual(int(layout["point_size"]), 16)
            self.assertGreaterEqual(int(layout["tree_size"]), 24)
            observations[name] = {
                "semantic": parsed["ABI"],
                "errors": parsed["ERRORS"],
                "layout": layout,
                "executable_bytes": fixture_executable(name).stat().st_size,
            }
        self.assertEqual(
            {key: value for key, value in observations["clang"]["semantic"].items() if key != "compiler"},
            {key: value for key, value in observations["gcc"]["semantic"].items() if key != "compiler"},
        )
        self.assertEqual(observations["clang"]["errors"], observations["gcc"]["errors"])

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
        unavailable = [name for name in ("clang", "gcc") if resolve_compiler(name) is None]
        if unavailable:
            self.skipTest("strict C23 compilers are unavailable: " + ", ".join(unavailable))
        for name in ("clang", "gcc"):
            result = build_with(name)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = run(["python", str(ROOT / "compare_semantics.py")])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["equal"])
        self.assertEqual([item["compiler"] for item in report["comparisons"]], ["clang", "gcc"])
        self.assertTrue(all(row["equal"] for item in report["comparisons"] for row in item["rows"]))
        for item in report["comparisons"]:
            comparable = [row for row in item["failures"] if row["comparable"]]
            native_only = [row for row in item["failures"] if not row["comparable"]]
            self.assertEqual(len(comparable), 3)
            self.assertTrue(all(row["equal"] for row in comparable))
            self.assertEqual(len(item["counterexamples"]), 0)
            self.assertEqual(len(native_only), 3)
            self.assertTrue(all(row["equal"] is None for row in native_only))

    def test_clang_address_sanitizer_proof(self):
        result = build_with("clang", sanitize=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        compiler = resolve_compiler("clang")
        llvm_runtime = asan_runtime_dir(compiler)
        self.assertIsNotNone(llvm_runtime, result.stdout)
        env = os.environ.copy()
        env["PATH"] = str(llvm_runtime) + os.pathsep + env.get("PATH", "")
        proof = run([str(executable("clang", sanitize=True))], env=env)
        self.assertEqual(proof.returncode, 0, proof.stdout + proof.stderr)
        self.assertIn("SUMMARY|failures=0", proof.stdout)

    def test_missing_asan_runtime_is_not_success(self):
        compiler = resolve_compiler("clang")
        llvm_runtime = asan_runtime_dir(compiler)
        self.assertIsNotNone(llvm_runtime)
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join(part for part in env.get("PATH", "").split(os.pathsep) if Path(part).resolve() != llvm_runtime.resolve())
        proof = run([str(executable("clang", sanitize=True))], env=env)
        self.assertNotEqual(proof.returncode, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", action="store_true")
    parser.parse_known_args()
    unittest.main(argv=["test_feasibility.py", "-v"])
