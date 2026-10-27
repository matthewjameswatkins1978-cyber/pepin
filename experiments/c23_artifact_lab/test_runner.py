from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import run_artifacts


class RunnerTests(unittest.TestCase):
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

    def test_receipt_parser_rejects_ambiguous_or_wrong_fixture_output(self):
        with self.assertRaises(ValueError):
            run_artifacts.parse_artifact_output("noise\n", "a05.fixture")
        with self.assertRaises(ValueError):
            run_artifacts.parse_artifact_output("ARTIFACT|fixture=other|status=success|value=42\n", "a05.fixture")


if __name__ == "__main__":
    unittest.main()
