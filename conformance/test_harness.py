"""Fast contract tests for the conformance harness itself.

The comprehensive laboratory is intentionally separate: these tests do not
launch Pep and should remain suitable for every repository test run that
explicitly selects the harness self-tests.
"""

from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from . import harness


class HarnessContractTests(unittest.TestCase):
    def test_timeout_bytes_are_decoded(self) -> None:
        timeout = subprocess.TimeoutExpired(["fake"], 0.01, output=b"partial\xff", stderr=b"err\xfe")
        with patch.object(harness.subprocess, "run", side_effect=timeout):
            result = harness.run_bounded(["fake"], timeout=0.01)
        self.assertEqual(result["status"], "timeout")
        self.assertIsInstance(result["stdout"], str)
        self.assertIsInstance(result["stderr"], str)
        self.assertIn("partial", result["stdout"])

    def test_malformed_output_is_not_a_response(self) -> None:
        self.assertIsNone(harness.response_from_stdout(b"not json\n{\"bad\":\n"))
        result = {
            "status": "completed", "returncode": 1, "stdout": "launcher failed\n",
            "stderr": "pwsh: command not found\n", "response": None,
        }
        classified = harness.classify_runtime_result(result, ["PEP_RUNTIME_DIVISION_BY_ZERO"])
        self.assertEqual(classified["classification"], "confirmed-bug")
        self.assertEqual(classified["outcome"], "launcher-or-malformed-output")
        self.assertIn("stderr", classified["evidence"])

    def test_wrong_runtime_diagnostic_is_detected_with_machine_evidence(self) -> None:
        result = {
            "status": "completed", "returncode": 1, "stdout": "{}", "stderr": "",
            "response": {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_OVERFLOW"}]},
        }
        classified = harness.classify_runtime_result(result, ["PEP_RUNTIME_DIVISION_BY_ZERO"])
        self.assertEqual(classified["classification"], "confirmed-bug")
        self.assertEqual(classified["outcome"], "wrong-diagnostic")
        self.assertEqual(classified["expectedCodes"], ["PEP_RUNTIME_DIVISION_BY_ZERO"])
        self.assertEqual(classified["actualCodes"], ["PEP_RUNTIME_OVERFLOW"])

    def test_exact_runtime_diagnostic_is_controlled(self) -> None:
        result = {
            "status": "completed", "returncode": 1, "stdout": "", "stderr": "",
            "response": {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_DIVISION_BY_ZERO"}]},
        }
        classified = harness.classify_runtime_result(result, ["PEP_RUNTIME_DIVISION_BY_ZERO"])
        self.assertEqual(classified["classification"], "expected-rejection")
        self.assertEqual(classified["outcome"], "controlled-runtime-failure")

    def test_reducer_is_deterministic_bounded_and_preserves_failure(self) -> None:
        original = b"prefix-KEEP-FAILURE-suffix"
        predicate = lambda value: b"KEEP-FAILURE" in value
        first, first_attempts = harness.reduce_bytes(original, predicate, budget=30)
        second, second_attempts = harness.reduce_bytes(original, predicate, budget=30)
        self.assertEqual(first, second)
        self.assertEqual(first_attempts, second_attempts)
        self.assertLessEqual(first_attempts, 30)
        self.assertTrue(predicate(first))
        self.assertLess(len(first), len(original))

    def test_runtime_replay_requires_the_original_wrong_diagnostic(self) -> None:
        finding = {
            "kind": "runtime-generator", "reason": "division by zero",
            "oracle": {"outcome": "wrong-diagnostic", "actualCodes": ["PEP_RUNTIME_OVERFLOW"]},
        }
        check = {"status": "completed", "returncode": 0,
                 "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        wrong = {"status": "completed", "returncode": 1,
                 "response": {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_OVERFLOW"}]},
                 "stdout": "", "stderr": ""}
        with patch.object(harness, "cli_case", side_effect=[check, wrong]):
            self.assertTrue(harness.replay_finding(finding, b"case", "runtime-case"))
        other = dict(wrong)
        other["response"] = {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_CALL_DEPTH"}]}
        with patch.object(harness, "cli_case", side_effect=[check, other]):
            self.assertFalse(harness.replay_finding(finding, b"case", "runtime-case"))

    def test_session_case_records_malformed_lines_without_crashing(self) -> None:
        fake = {"status": "completed", "returncode": 0, "stdout": "not-json\n{\"status\":\"valid\"}\n", "stderr": "", "elapsedMs": 1}
        with patch.object(harness, "run_bounded", return_value=fake):
            result = harness.session_case([{"op": "open", "source": "say(\"x\")\n"}])
        self.assertEqual(result["responses"][0]["_malformedResponse"], "not-json")
        self.assertEqual(result["responses"][1]["status"], "valid")


if __name__ == "__main__":
    unittest.main()
