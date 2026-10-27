from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
import measure_artifacts
from run_artifacts import ProcessResult


class MeasurementTests(unittest.TestCase):
    def test_each_warmup_and_trial_has_an_independent_oracle(self):
        fixture_id = "a05.measure"
        expected = {"status": "success", "value": 42}
        receipt = "ARTIFACT|fixture=a05.measure|status=success|value=42\n"
        calls = []

        def fake_run(command, timeout, cwd):
            calls.append((command, timeout, cwd))
            return ProcessResult("completed", 0, receipt, "", False)

        with mock.patch.object(measure_artifacts, "run_process", side_effect=fake_run):
            warmup = measure_artifacts.verify_execution(Path(sys.executable), fixture_id, expected, Path.cwd(), 1, "warmup", 0)
            trial = measure_artifacts.verify_execution(Path(sys.executable), fixture_id, expected, Path.cwd(), 1, "trial", 0)

        self.assertTrue(warmup["match"])
        self.assertTrue(trial["match"])
        self.assertEqual(len(calls), 2)
        self.assertEqual({record["phase"] for record in (warmup, trial)}, {"warmup", "trial"})

    def test_malformed_output_is_a_failed_run_even_if_exit_is_zero(self):
        with mock.patch.object(measure_artifacts, "run_process", return_value=ProcessResult("completed", 0, "noise\n", "", False)):
            record = measure_artifacts.verify_execution(Path(sys.executable), "a05.measure", {"status": "success", "value": 42}, Path.cwd(), 1, "trial", 0)
        self.assertFalse(record["match"])
        self.assertIn("error", record)


if __name__ == "__main__":
    unittest.main()
