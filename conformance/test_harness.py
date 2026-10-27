"""Fast contract tests for the conformance harness itself.

The comprehensive laboratory is intentionally separate: these tests do not
launch Pep and should remain suitable for every repository test run that
explicitly selects the harness self-tests.
"""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import harness
from .generator import INT_MAX, INT_MIN, ArithmeticFault, boundary_vectors, checked_neg, generate_cases
from .metamorphic import MetamorphicPair, compare_pair, pairs_for_case, semantic_signature
from .session_history import generate_histories, reduce_history, validate_history


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

    def test_metamorphic_relations_are_deterministic_and_span_aware(self) -> None:
        case = generate_cases(7, 1, 1)[0]
        first = pairs_for_case(case)
        second = pairs_for_case(case)
        self.assertEqual(first, second)
        self.assertEqual({pair.relation for pair in first}, {"line-ending", "trailing-comments"})
        self.assertNotEqual(first[0].original, first[0].transformed)
        left = {"status": "valid", "revision": "sha256:a", "span": {"start": 1}, "typed": {"type": "Int"}}
        right = {"status": "valid", "revision": "sha256:b", "span": {"start": 99}, "typed": {"type": "Int"}}
        self.assertEqual(semantic_signature(left), semantic_signature(right))

    def test_metamorphic_synthetic_mismatch_is_classified(self) -> None:
        left = {"status": "completed", "returncode": 0,
                "response": {"status": "valid", "typed": {"type": "Int"}}}
        right = {"status": "completed", "returncode": 0,
                 "response": {"status": "invalid", "diagnostics": [{"code": "PEP_PARSE"}]}}
        finding = compare_pair(left, right, "1\n", "1\n")
        self.assertEqual(finding["classification"], "confirmed-bug")
        self.assertIn("semantic", finding["detail"])

    def test_metamorphic_runner_records_preserved_relation_and_fails_wrong_output(self) -> None:
        case = generate_cases(7, 1, 1)[0]
        pair = MetamorphicPair("pair-1", case.case_id, "line-ending", case.source,
                               case.source.replace(b"\n", b"\r\n"), case.expected_output)
        check = {"status": "completed", "returncode": 0,
                 "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        good_run = {"status": "completed", "returncode": 0, "stdout": case.expected_output,
                    "stderr": "", "response": {"status": "valid"}}
        bad_run = dict(good_run)
        bad_run["stdout"] = "wrong\n"
        findings: list[dict[str, object]] = []
        stats = self._grammar_stats() | {"metamorphicPairs": 0, "metamorphicPreserved": 0}
        with patch.object(harness, "generate_cases", return_value=(case,)), \
             patch.object(harness, "pairs_for_case", return_value=(pair,)), \
             patch.object(harness, "cli_case", side_effect=[check, check, good_run, bad_run]):
            harness.run_metamorphic(7, 1, 1, findings, stats)
        self.assertEqual(stats["metamorphicPairs"], 1)
        self.assertEqual(findings[0]["classification"], "confirmed-bug")

    def test_metamorphic_completed_nonzero_is_compiler_finding_and_launch_is_infrastructure(self) -> None:
        completed = {"status": "completed", "returncode": 0,
                     "response": {"status": "valid"}, "stdout": "", "stderr": ""}
        pair = MetamorphicPair("pair-2", "case-2", "line-ending", b"say(1)\n", b"say(1)\r\n", "1\n")
        for transformed, expected_classification in (
                ({"status": "completed", "returncode": 2, "stdout": "", "stderr": "",
                  "response": {"status": "valid"}}, "confirmed-bug"),
                ({"status": "launch-error", "returncode": None, "stdout": "", "stderr": "",
                  "error": {"type": "FileNotFoundError"}}, "infrastructure-failure")):
            findings: list[dict[str, object]] = []
            stats = self._grammar_stats() | {"metamorphicPairs": 0, "metamorphicPreserved": 0}
            with patch.object(harness, "generate_cases", return_value=(generate_cases(7, 1, 1)[0],)), \
                 patch.object(harness, "pairs_for_case", return_value=(pair,)), \
                 patch.object(harness, "cli_case", side_effect=[completed, completed, completed, transformed]):
                harness.run_metamorphic(7, 1, 1, findings, stats)
            self.assertEqual(findings[0]["classification"], expected_classification)
            self.assertEqual(harness.failed_finding_count(findings), 1)

    def test_metamorphic_same_wrong_output_is_not_preserved(self) -> None:
        left = {"status": "completed", "returncode": 0, "response": {"status": "valid"}}
        right = {"status": "completed", "returncode": 0, "response": {"status": "valid"}}
        finding = compare_pair(left, right, "wrong\n", "wrong\n", expected_output="right\n")
        self.assertEqual(finding["classification"], "confirmed-bug")

    @staticmethod
    def _complete_history_result(history):
        hole = {"name": history.hole_name, "expectedType": "Int"}
        initial = {"outcome": "ok", "operation": "open", "document": history.expected_document,
                   "revision": history.original_revision, "status": "incomplete", "typedTree": {},
                   "holes": [hole], "diagnostics": []}
        query = {**initial, "operation": "query"}
        metrics = {"outcome": "ok", "operation": "metrics", "metrics": {"cache_hits": 2}}
        edit = {"outcome": "ok", "operation": "apply_edit", "document": history.expected_document,
                "revision": history.filled_revision, "status": "valid", "typedTree": {},
                "holes": [], "diagnostics": []}
        stale = {"outcome": "error", "operation": "apply_edit", "document": history.expected_document,
                 "currentRevision": history.filled_revision,
                 "error": {"code": "PEP_STALE_REVISION"}}
        current = {"outcome": "ok", "operation": "query", "document": history.expected_document,
                   "revision": history.filled_revision, "status": "valid", "typedTree": {},
                   "holes": [], "diagnostics": []}
        malformed = {"outcome": "error", "operation": "session",
                     "error": {"code": "PEP_SESSION_MALFORMED_JSON"}}
        recovery = {"outcome": "ok", "operation": "open", "document": "doc-2",
                    "revision": history.recovery_revision, "status": "valid", "typedTree": {},
                    "holes": [], "diagnostics": []}
        return {"status": "completed", "returncode": 0,
                "responses": [initial, query, copy.deepcopy(query), metrics, edit, stale,
                              current, malformed, recovery]}

    def test_session_history_validator_accepts_and_checks_every_state_transition(self) -> None:
        history = generate_histories(9, 1)[0]
        result = self._complete_history_result(history)
        finding = validate_history(result, history, lambda response: response.get("status"))
        self.assertEqual(finding["classification"], "missing-test")
        self.assertEqual(finding["failureSignature"], "history-preserved")

        mutations = (
            (0, "document", "other", "initial-open-revision"),
            (1, "revision", "other", "original-query-shape"),
            (4, "outcome", "error", "edit-failed"),
            (5, "currentRevision", "other", "stale-state-mismatch"),
            (5, "error", {"code": "PEP_WRONG"}, "stale-error-mismatch"),
            (6, "holes", [{"name": history.hole_name}], "current-query-hole"),
            (7, "error", {"code": "PEP_WRONG"}, "malformed-json-recovery-failed"),
            (8, "revision", "other", "recovery-identity-mismatch"),
        )
        for index, key, value, signature in mutations:
            candidate = copy.deepcopy(result)
            candidate["responses"][index][key] = value
            finding = validate_history(candidate, history, lambda response: response.get("status"))
            self.assertEqual(finding["classification"], "confirmed-bug", signature)
            self.assertEqual(finding["failureSignature"], signature, signature)

    def test_session_history_reducer_replays_real_sequence_and_preserves_signature(self) -> None:
        history = generate_histories(9, 1)[0]
        baseline = self._complete_history_result(history)["responses"]
        baseline[5]["error"]["code"] = "PEP_WRONG_STALE"

        def fake_session(requests):
            responses = []
            for request in requests:
                index = history.requests.index(request)
                responses.append(copy.deepcopy(baseline[index]))
            return {"status": "completed", "returncode": 0, "responses": responses}

        findings: list[dict[str, object]] = []
        stats = {"sessionHistories": 0, "sessionHistoryRequests": 0, "classificationCounts": {}}
        with TemporaryDirectory() as directory, patch.object(harness, "OUT", Path(directory)), \
             patch.object(harness, "generate_histories", return_value=(history,)), \
             patch.object(harness, "session_case", side_effect=fake_session):
            harness.run_session_histories(9, 1, findings, stats)
            self.assertEqual(findings[0]["failureSignature"], "stale-error-mismatch")
            harness.reduce_findings(findings, max_cases=1, stats=stats)
            reduction = findings[0]["reduction"]
            self.assertEqual(reduction["status"], "reduced")
            self.assertEqual(reduction["failureSignature"], "stale-error-mismatch")
            self.assertLess(findings[0]["reducedRequestCount"], 9)
            self.assertLessEqual(reduction["attempts"], 80)
            self.assertTrue((Path(directory) / findings[0]["reducedTranscript"]).exists())
            self.assertEqual(findings[0]["reducedRequestCount"], 3)

    def test_session_histories_and_reducer_are_deterministic_and_bounded(self) -> None:
        first = generate_histories(9, 2)
        second = generate_histories(9, 2)
        self.assertEqual(first, second)
        self.assertEqual(len(first[0].requests), 9)
        self.assertEqual(first[0].expected_codes, ((5, "PEP_STALE_REVISION"),
                                                   (7, "PEP_SESSION_MALFORMED_JSON")))
        predicate = lambda items: "KEEP" in items
        original = ("noise-a", "KEEP", "noise-b", "noise-c")
        reduced, attempts = reduce_history(original, predicate, budget=20)
        reduced_again, attempts_again = reduce_history(original, predicate, budget=20)
        self.assertEqual(reduced, reduced_again)
        self.assertEqual(attempts, attempts_again)
        self.assertTrue(predicate(reduced))
        self.assertLessEqual(attempts, 20)
        self.assertEqual(reduced, ("KEEP",))

    def test_session_history_validator_rejects_wrong_error_without_crashing(self) -> None:
        history = generate_histories(9, 1)[0]
        result = self._complete_history_result(history)
        result["responses"][5]["error"]["code"] = "PEP_WRONG"
        finding = validate_history(result, history, lambda response: response.get("status"))
        self.assertEqual(finding["classification"], "confirmed-bug")
        self.assertEqual(finding["actualCode"], "PEP_WRONG")

    def test_session_history_runner_propagates_finding_classification(self) -> None:
        history = generate_histories(9, 1)[0]
        findings: list[dict[str, object]] = []
        stats = {"sessionHistories": 0, "sessionHistoryRequests": 0, "classificationCounts": {}}
        with patch.object(harness, "generate_histories", return_value=(history,)), \
             patch.object(harness, "session_case", return_value={"status": "completed", "returncode": 0, "responses": []}), \
             patch.object(harness, "validate_history", return_value={"classification": "confirmed-bug", "detail": "synthetic history mismatch"}):
            harness.run_session_histories(9, 1, findings, stats)
        self.assertEqual(stats["sessionHistories"], 1)
        self.assertEqual(stats["sessionHistoryRequests"], 9)
        self.assertEqual(findings[0]["classification"], "confirmed-bug")
        self.assertEqual(harness.failed_finding_count(findings), 1)


if __name__ == "__main__":
    unittest.main()
