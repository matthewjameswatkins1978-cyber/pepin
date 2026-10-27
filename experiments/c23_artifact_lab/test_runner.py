from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import run_artifacts


class RunnerTests(unittest.TestCase):
    def test_discovery_matrix_covers_path_override_and_partial_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clang = root / "clang.exe"
            gcc = root / "gcc.exe"
            clang.write_bytes(b"clang")
            gcc.write_bytes(b"gcc")
            original = dict(run_artifacts.KNOWN)
            run_artifacts.KNOWN["clang"] = []
            run_artifacts.KNOWN["gcc"] = []
            try:
                both = lambda name: str(clang if name == "clang" else gcc)
                self.assertEqual(run_artifacts.discover_compiler("clang", {}, both), str(clang))
                self.assertEqual(run_artifacts.discover_compiler("gcc", {}, both), str(gcc))
                self.assertEqual(run_artifacts.discover_compiler("clang", {"PEP_C23_CLANG": str(clang)}, lambda _name: None), str(clang))
                self.assertIsNone(run_artifacts.discover_compiler("gcc", {}, lambda _name: None))
            finally:
                run_artifacts.KNOWN.clear()
                run_artifacts.KNOWN.update(original)

    def test_explicit_compiler_path_wins_and_missing_is_not_available(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "clang.exe"
            fake.write_bytes(b"synthetic compiler marker")
            original = list(run_artifacts.KNOWN["clang"])
            run_artifacts.KNOWN["clang"] = []
            try:
                self.assertEqual(run_artifacts.discover_compiler("clang", {"PEP_C23_CLANG": str(fake)}, lambda _name: None), str(fake))
                self.assertIsNone(run_artifacts.discover_compiler("clang", {}, lambda _name: None))
            finally:
                run_artifacts.KNOWN["clang"] = original

    def test_process_failure_and_timeout_are_distinct(self):
        root = Path.cwd()
        state, code, _output, timed_out = run_artifacts.run_process([sys.executable, "-c", "import sys; sys.exit(7)"], 2, root)
        self.assertEqual((state, code, timed_out), ("completed", 7, False))
        state, code, _output, timed_out = run_artifacts.run_process([sys.executable, "-c", "import time; time.sleep(5)"], 0.01, root)
        self.assertEqual(state, "timeout")
        self.assertIsNone(code)
        self.assertTrue(timed_out)

    def test_timeout_validation_and_partial_bytes_are_preserved(self):
        root = Path.cwd()
        with self.assertRaises(ValueError):
            run_artifacts.run_process([sys.executable, "-c", ""], 0, root)
        with self.assertRaises(ValueError):
            run_artifacts.run_process([sys.executable, "-c", ""], float("inf"), root)
        command = [sys.executable, "-c", "pass"]
        timeout = run_artifacts.subprocess.TimeoutExpired(command, 1, output=b"partial", stderr=b"diagnostic")
        with mock.patch.object(run_artifacts.subprocess, "run", side_effect=timeout):
            result = run_artifacts.run_process(command, 0.01, root)
        self.assertEqual(result.state, "timeout")
        self.assertEqual(result.stdout, "partial")
        self.assertEqual(result.stderr, "diagnostic")

    def test_compiler_identity_failure_is_structured(self):
        identity = run_artifacts.compiler_version(str(Path.cwd() / "missing-compiler.exe"), 1, Path.cwd())
        self.assertEqual(identity["status"], "unavailable")

    def test_receipt_parser_rejects_ambiguous_or_wrong_fixture_output(self):
        with self.assertRaises(ValueError):
            run_artifacts.parse_artifact_output("noise\n", "a05.fixture")
        with self.assertRaises(ValueError):
            run_artifacts.parse_artifact_output("ARTIFACT|fixture=other|status=success|value=42\n", "a05.fixture")
        with self.assertRaises(ValueError):
            run_artifacts.parse_artifact_output("ARTIFACT|fixture=a05.fixture|status=success|value=42\nnoise\n", "a05.fixture")


if __name__ == "__main__":
    unittest.main()
