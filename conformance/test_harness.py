"""Fast contract tests for the conformance harness itself.

The comprehensive laboratory is intentionally separate: these tests do not
launch Pep and should remain suitable for every repository test run that
explicitly selects the harness self-tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import harness
from .generator import INT_MAX, INT_MIN, ArithmeticFault, boundary_vectors, checked_neg, generate_cases


class HarnessContractTests(unittest.TestCase):
    @staticmethod
    def _runner_stats() -> dict[str, object]:
        return {"validGenerated": 0, "invalidGenerated": 0, "runtimeGenerated": 0,
                "expectedRejection": 0, "controlledRuntimeFailures": 0,
                "classificationCounts": {}}

    @staticmethod
    def _runner_report(findings: list[dict[str, object]], stats: dict[str, object]) -> str:
        return harness.report_text({"revision": "test", "branch": "test", "seeds": [1],
                                    "timeoutSeconds": 1, "stats": stats, "findings": findings,
                                    "inheritedA11": None})

    def test_runner_rejected_valid_runtime_case_is_fatal(self) -> None:
        source = b"say(int_text(1 / 0))\n"
        check = {"status": "completed", "returncode": 1,
                 "response": {"status": "invalid", "diagnostics": [{"code": "PEP_PARSE"}]}}
        findings: list[dict[str, object]] = []
        stats = self._runner_stats()
        with patch.object(harness, "valid_sources", return_value=[]), \
             patch.object(harness, "invalid_sources", return_value=[]), \
             patch.object(harness, "runtime_sources", return_value=[("runtime-1-0000", source, "division by zero")]), \
             patch.object(harness, "cli_case", return_value=check) as cli:
            harness.run_generated(1, 1, findings, stats)
        self.assertEqual(cli.call_count, 1)
        self.assertEqual(findings[0]["classification"], "confirmed-bug")
        self.assertEqual(harness.failed_finding_count(findings), 1)
        self.assertIn("**confirmed-bug**", self._runner_report(findings, stats))

    def test_runner_propagates_runtime_infrastructure_failure_and_fails(self) -> None:
        source = b"say(int_text(1 / 0))\n"
        check = {"status": "completed", "returncode": 0,
                 "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        launch = {"status": "launch-error", "returncode": None, "stdout": "", "stderr": "",
                  "error": {"type": "FileNotFoundError", "message": "pwsh"}}
        findings: list[dict[str, object]] = []
        stats = self._runner_stats()
        with patch.object(harness, "valid_sources", return_value=[]), \
             patch.object(harness, "invalid_sources", return_value=[]), \
             patch.object(harness, "runtime_sources", return_value=[("runtime-1-0000", source, "division by zero")]), \
             patch.object(harness, "cli_case", side_effect=[check, launch]):
            harness.run_generated(1, 1, findings, stats)
        self.assertEqual(findings[0]["classification"], "infrastructure-failure")
        self.assertEqual(harness.failed_finding_count(findings), 1)
        report = self._runner_report(findings, stats)
        self.assertIn("**infrastructure-failure**", report)
        self.assertNotIn("**confirmed-bug**", report)

    def test_runner_keeps_wrong_diagnostic_fatal_and_expected_runtime_rejection(self) -> None:
        source = b"say(int_text(1 / 0))\n"
        check = {"status": "completed", "returncode": 0,
                 "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        wrong = {"status": "completed", "returncode": 1, "stdout": "", "stderr": "",
                 "response": {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_OVERFLOW"}]}}
        expected = {"status": "completed", "returncode": 1, "stdout": "", "stderr": "",
                    "response": {"status": "runtime_error", "diagnostics": [{"code": "PEP_RUNTIME_DIVISION_BY_ZERO"}]}}
        for execution, expected_classification in ((wrong, "confirmed-bug"), (expected, None)):
            findings: list[dict[str, object]] = []
            stats = self._runner_stats()
            with patch.object(harness, "valid_sources", return_value=[]), \
                 patch.object(harness, "invalid_sources", return_value=[]), \
                 patch.object(harness, "runtime_sources", return_value=[("runtime-1-0000", source, "division by zero")]), \
                 patch.object(harness, "cli_case", side_effect=[check, execution]):
                harness.run_generated(1, 1, findings, stats)
            if expected_classification:
                self.assertEqual(findings[0]["classification"], expected_classification)
                self.assertEqual(harness.failed_finding_count(findings), 1)
            else:
                self.assertEqual(findings, [])
                self.assertEqual(stats["controlledRuntimeFailures"], 1)

    def test_timeout_bytes_are_decoded(self) -> None:
        timeout = subprocess.TimeoutExpired(["fake"], 0.01, output=b"partial\xff", stderr=b"err\xfe")
        with patch.object(harness.subprocess, "run", side_effect=timeout):
            result = harness.run_bounded(["fake"], timeout=0.01)
        self.assertEqual(result["status"], "timeout")
        self.assertIsInstance(result["stdout"], str)
        self.assertIsInstance(result["stderr"], str)
        self.assertIn("partial", result["stdout"])

    def test_launch_exception_is_structured_and_fails_as_infrastructure(self) -> None:
        error = FileNotFoundError(2, "No such file or directory", "pwsh")
        with patch.object(harness.subprocess, "run", side_effect=error):
            result = harness.run_bounded(["pwsh", "missing"], timeout=0.01)
        self.assertEqual(result["status"], "launch-error")
        self.assertEqual(result["error"]["type"], "FileNotFoundError")
        self.assertEqual(harness.transport_failure_classification(result), "infrastructure-failure")

    def test_invalid_check_classifier_rejects_tuple_truthiness_false_passes(self) -> None:
        rejected = {"status": "completed", "returncode": 1,
                    "response": {"status": "invalid", "diagnostics": [{"code": "PEP_PARSE"}]}}
        self.assertEqual(harness.classify_invalid_check(rejected)["classification"], "expected-rejection")
        for malformed in (
            {"status": "completed", "returncode": 1, "response": None},
            {"status": "completed", "returncode": 0,
             "response": {"status": "invalid", "diagnostics": [{"code": "PEP_PARSE"}]}},
            {"status": "launch-error", "returncode": None, "response": None},
        ):
            self.assertNotEqual(harness.classify_invalid_check(malformed)["classification"], "expected-rejection")

    def test_empty_and_malformed_diagnostics_are_rejected_without_index_error(self) -> None:
        empty = {"status": "completed", "returncode": 1,
                 "response": {"status": "invalid", "diagnostics": []}}
        malformed = {"status": "completed", "returncode": 1,
                     "response": {"status": "invalid", "diagnostics": {"code": "PEP_PARSE"}}}
        self.assertFalse(harness.check_result_contract(empty)[0])
        self.assertFalse(harness.check_result_contract(malformed)[0])
        runtime = {"status": "completed", "returncode": 1, "stdout": "", "stderr": "",
                   "response": {"status": "runtime_error", "diagnostics": []}}
        self.assertEqual(harness.classify_runtime_result(runtime, ["PEP_RUNTIME_OVERFLOW"])["outcome"], "wrong-diagnostic")

    def test_large_response_wrong_error_fails_and_documented_error_passes(self) -> None:
        wrong = {"status": "completed", "returncode": 0, "stdout": "{}", "responses": [{"error": {"code": "PEP_OTHER"}}]}
        correct = {"status": "completed", "returncode": 0, "stdout": "{}", "responses": [{"error": {"code": "PEP_TOOL_MESSAGE_TOO_LARGE"}}]}
        self.assertEqual(harness.classify_large_response(wrong)["classification"], "confirmed-bug")
        self.assertEqual(harness.classify_large_response(correct)["classification"], "expected-rejection")

    def test_malformed_output_is_not_a_response(self) -> None:
        self.assertIsNone(harness.response_from_stdout(b"not json\n{\"bad\":\n"))
        result = {
            "status": "completed", "returncode": 1, "stdout": "launcher failed\n",
            "stderr": "pwsh: command not found\n", "response": None,
        }
        classified = harness.classify_runtime_result(result, ["PEP_RUNTIME_DIVISION_BY_ZERO"])
        self.assertEqual(classified["classification"], "infrastructure-failure")
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

    def test_reduce_findings_reruns_oracle_and_writes_only_preserved_bytes(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            corpus = output / "corpus"
            corpus.mkdir()
            (corpus / "invalid-case.pep").write_bytes(b"prefix-FAIL-suffix")
            finding = {"caseId": "invalid-case", "kind": "invalid-generator", "classification": "confirmed-bug"}

            def fake_cli(case_id: str, raw: bytes, command: str = "check") -> dict[str, object]:
                return {"status": "completed", "returncode": 0 if b"FAIL" in raw else 1,
                        "response": {"status": "valid" if b"FAIL" in raw else "invalid"},
                        "stdout": "", "stderr": ""}

            with patch.object(harness, "ROOT", output), patch.object(harness, "OUT", output), patch.object(harness, "cli_case", side_effect=fake_cli):
                harness.reduce_findings([finding], max_cases=1)
            reduced = (output / "counterexamples" / "invalid-case.pep").read_bytes()
            self.assertEqual(reduced, b"FAIL")
            self.assertEqual(finding["reduction"]["status"], "reduced")
            self.assertLessEqual(finding["reduction"]["attempts"], 80)

    def test_unsupported_finding_retains_original_without_counterexample(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory)
            corpus = output / "corpus"
            corpus.mkdir()
            (corpus / "session-case.pep").write_bytes(b"original")
            finding = {"caseId": "session-case", "kind": "session", "classification": "confirmed-bug"}
            with patch.object(harness, "OUT", output):
                harness.reduce_findings([finding], max_cases=1)
            self.assertEqual(finding["reduction"]["status"], "unsupported")
            self.assertFalse((output / "counterexamples").exists())

    def test_session_case_records_malformed_lines_without_crashing(self) -> None:
        fake = {"status": "completed", "returncode": 0, "stdout": "not-json\n{\"status\":\"valid\"}\n", "stderr": "", "elapsedMs": 1}
        with patch.object(harness, "run_bounded", return_value=fake):
            result = harness.session_case([{"op": "open", "source": "say(\"x\")\n"}])
        self.assertEqual(result["responses"][0]["_malformedResponse"], "not-json")
        self.assertEqual(result["responses"][1]["status"], "valid")

    def test_grammar_corpus_is_deterministic_and_pairs_valid_invalid_cases(self) -> None:
        first = generate_cases(42, 6, 2)
        second = generate_cases(42, 6, 2)
        self.assertEqual(first, second)
        self.assertEqual([case.validity for case in first], ["valid", "invalid"] * 6)
        self.assertEqual(len({case.case_id for case in first}), len(first))
        self.assertTrue({case.family for case in first} >= {"records", "recursive-union-match", "lists-for-in"})

    def test_integer_reference_model_covers_signed_64_bit_boundaries(self) -> None:
        vectors = {vector.name: vector for vector in boundary_vectors()}
        self.assertEqual(vectors["add-max"].value, INT_MAX)
        self.assertEqual(vectors["sub-min"].value, INT_MIN)
        self.assertEqual(vectors["div-min"].value, INT_MIN)
        self.assertEqual(vectors["add-overflow"].error_code, "PEP_RUNTIME_OVERFLOW")
        self.assertEqual(vectors["div-overflow"].error_code, "PEP_RUNTIME_OVERFLOW")
        self.assertEqual(vectors["div-zero"].error_code, "PEP_RUNTIME_DIVISION_BY_ZERO")
        with self.assertRaises(ArithmeticFault):
            checked_neg(INT_MIN)

    @staticmethod
    def _grammar_stats() -> dict[str, object]:
        return {"grammarGenerated": 0, "grammarValid": 0, "grammarInvalid": 0,
                "grammarExpectedOutput": 0, "grammarExpectedRejection": 0,
                "grammarBoundaryVectors": 10, "classificationCounts": {}}

    def test_grammar_runner_rejected_valid_case_is_fatal(self) -> None:
        case = generate_cases(7, 1, 1)[0]
        check = {"status": "completed", "returncode": 1,
                 "response": {"status": "invalid", "diagnostics": [{"code": "PEP_PARSE"}]}}
        findings: list[dict[str, object]] = []
        stats = self._grammar_stats()
        with patch.object(harness, "generate_cases", return_value=(case,)), \
             patch.object(harness, "cli_case", return_value=check):
            harness.run_grammar_generated(7, 1, 1, findings, stats)
        self.assertEqual(findings[0]["classification"], "confirmed-bug")
        self.assertEqual(harness.failed_finding_count(findings), 1)

    def test_grammar_runner_accepts_only_exact_invalid_contract(self) -> None:
        case = generate_cases(7, 1, 1)[1]
        malformed = {"status": "completed", "returncode": 1,
                     "response": {"status": "invalid", "diagnostics": []}}
        findings: list[dict[str, object]] = []
        stats = self._grammar_stats()
        with patch.object(harness, "generate_cases", return_value=(case,)), \
             patch.object(harness, "cli_case", return_value=malformed):
            harness.run_grammar_generated(7, 1, 1, findings, stats)
        self.assertEqual(findings[0]["classification"], "infrastructure-failure")
        self.assertEqual(harness.failed_finding_count(findings), 1)

    def test_grammar_runner_requires_independent_runtime_output(self) -> None:
        case = generate_cases(7, 1, 1)[0]
        check = {"status": "completed", "returncode": 0,
                 "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        run = {"status": "completed", "returncode": 0, "stdout": "wrong\n", "stderr": "",
               "response": {"status": "valid"}}
        findings: list[dict[str, object]] = []
        stats = self._grammar_stats()
        with patch.object(harness, "generate_cases", return_value=(case,)), \
             patch.object(harness, "cli_case", side_effect=[check, run]):
            harness.run_grammar_generated(7, 1, 1, findings, stats)
        self.assertEqual(findings[0]["classification"], "confirmed-bug")
        self.assertEqual(findings[0]["expected"], case.expected_output)


if __name__ == "__main__":
    unittest.main()
