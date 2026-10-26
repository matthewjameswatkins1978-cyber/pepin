import argparse
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def run(command, cwd=REPO):
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


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


class InterpreterOracleTests(unittest.TestCase):
    def assert_pep_output(self, source, expected):
        result = run(["pwsh", "-File", str(REPO / "pep.ps1"), "run", str(REPO / source)])
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


class NativeProofTests(unittest.TestCase):
    def test_native_proof_when_compilers_exist(self):
        compilers = [name for name in ("clang", "gcc") if shutil.which(name)]
        if not compilers:
            self.skipTest("strict C23 compilers are not installed on this host")
        result = run(["pwsh", "-File", str(ROOT / "build.ps1"), "-Compiler", "all"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in compilers:
            executable = ROOT.parents[1] / "_build" / "c23-feasibility" / name / "pep_c23_probe.exe"
            self.assertTrue(executable.exists(), result.stdout)
            proof = run([str(executable)])
            self.assertEqual(proof.returncode, 0, proof.stdout + proof.stderr)
            self.assertIn("SUMMARY|failures=0", proof.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", action="store_true")
    parser.parse_known_args()
    unittest.main(argv=["test_feasibility.py", "-v"])
