import json
import copy
import pathlib
import unittest
import sys
import time
from dataclasses import replace

from tests import integration01_lab as lab


class Integration01LabTests(unittest.TestCase):
    def _child(self, source: str, timeout: float = 1.0):
        return lab.performance.JsonlSession(
            pathlib.Path(lab.ROOT), response_timeout_s=timeout,
            command=[sys.executable, "-c", source],
        )

    def test_manifest_keeps_accepted_and_unaccepted_stages_distinct(self):
        manifest = lab.validate_manifest()
        self.assertEqual(manifest["limits"]["sourceBytes"], 65536)
        a12 = next(entry for entry in manifest["inputs"] if entry["name"] == "A12 parser")
        self.assertEqual(a12["sha"], "69a47fe77187666bdd045b8dc8a9f633a7dd49d7")
        a13 = next(entry for entry in manifest["inputs"] if entry["name"] == "A13 checker")
        self.assertIsNone(a13["sha"])

    def test_manifest_rejects_a13_promotion(self):
        manifest = lab.load_manifest()
        mutated = json.loads(json.dumps(manifest))
        a13 = next(entry for entry in mutated["inputs"] if entry["name"] == "A13 checker")
        a13["status"] = "accepted"
        with self.assertRaises(lab.IntegrationError):
            lab.validate_manifest(mutated)

    def test_matrix_has_independent_expected_outcomes(self):
        matrix = lab.validate_matrix()
        self.assertGreaterEqual(len(matrix["cases"]), 15)
        self.assertIn("subprocess exit alone is never success", matrix["oracleRule"])

    def test_contract_keeps_syntax_and_semantic_authority_separate(self):
        contract = lab.validate_contract()
        self.assertIn("document", contract["syntaxInputFromA12"])
        self.assertIn("resolvedCallTarget", contract["a13FactsRequiredBeforeCheckerConsumer"])
        self.assertIn("syntaxIdUsedAsSemanticId", contract["mustRejectOrDefer"])

    def test_contract_rejects_limit_drift(self):
        contract = lab.load_contract()
        mutated = json.loads(json.dumps(contract))
        mutated["limits"]["sourceBytes"] = 131072
        with self.assertRaises(lab.IntegrationError):
            lab.validate_contract(mutated)

    def test_matrix_rejects_duplicate_case_ids(self):
        matrix = lab.load_matrix()
        mutated = json.loads(json.dumps(matrix))
        mutated["cases"].append(mutated["cases"][0])
        with self.assertRaises(lab.IntegrationError):
            lab.validate_matrix(mutated)

    def test_span_check_rejects_out_of_source_bounds(self):
        with self.assertRaises(lab.IntegrationError):
            lab._span_check([{"span": {"start": 0, "end": 9}}], 8)

    def test_full_gate_rejects_record_with_invalid_status(self):
        real = lab.performance.parse_source
        cache = {}

        def forged(source):
            measurement = cache.setdefault(source, real(source))
            if isinstance(source, str) and source.startswith("type Point"):
                return replace(measurement, status="invalid")
            return measurement

        with self.assertRaises(lab.IntegrationError):
            lab.run_a12_boundary(forged)

    def test_full_gate_rejects_unicode_with_incomplete_status(self):
        real = lab.performance.parse_source
        cache = {}

        def forged(source):
            measurement = cache.setdefault(source, real(source))
            if isinstance(source, bytes) and b"caf" in source:
                return replace(measurement, status="incomplete")
            return measurement

        with self.assertRaises(lab.IntegrationError):
            lab.run_a12_boundary(forged)

    def test_exact_ast_oracle_rejects_field_operator_value_role_span_and_chunk_mutations(self):
        record_source = (
            "type Point { x: Int, y: Int }\n"
            "fn main() -> Int { let point = Point { x: 1, y: 2 }; return point.x }"
        )
        measurement = lab.performance.parse_source(record_source)

        def reject(mutated):
            with self.assertRaises(AssertionError):
                lab.verify_measurement("mutated", record_source, mutated, expected_status="complete")

        ast_operator = copy.deepcopy(measurement.target_ast)
        ast_operator[1]["body"][0]["value"]["fields"][0]["value"]["value"] = 99
        reject(replace(measurement, target_ast=ast_operator))

        ast_field = copy.deepcopy(measurement.target_ast)
        ast_field[0]["fields"][0]["name"] = "wrong"
        reject(replace(measurement, target_ast=ast_field))

        nodes = copy.deepcopy(measurement.nodes)
        nodes[0]["role"] = "wrong_role"
        reject(replace(measurement, nodes=nodes))

        nodes = copy.deepcopy(measurement.nodes)
        nodes[0]["span"]["start"] = 999
        reject(replace(measurement, nodes=nodes))

        reject(replace(measurement, nodes=measurement.nodes[:-1]))
        reject(replace(measurement, nodes=measurement.nodes + [copy.deepcopy(measurement.nodes[-1])]))

    def test_exact_ast_oracle_rejects_arithmetic_operator_and_literal_mutations(self):
        source = "1 + 2 * 3 - 4"
        measurement = lab.performance.parse_source(source)

        ast_operator = copy.deepcopy(measurement.target_ast)
        ast_operator[0]["value"]["operator"] = "/"
        with self.assertRaises(lab.IntegrationError):
            lab.verify_measurement("operator", source, replace(measurement, target_ast=ast_operator), expected_status="complete")

        ast_literal = copy.deepcopy(measurement.target_ast)
        ast_literal[0]["value"]["left"]["left"]["value"] = 99
        with self.assertRaises(lab.IntegrationError):
            lab.verify_measurement("literal", source, replace(measurement, target_ast=ast_literal), expected_status="complete")

    def test_jsonl_timeout_terminates_nonresponsive_child_with_partial_evidence(self):
        session = self._child("import sys, time; sys.stdin.readline(); time.sleep(10)", timeout=0.1)
        started = time.perf_counter()
        try:
            with self.assertRaises(lab.performance.SessionResponseTimeout) as caught:
                session.send({"request": "never-replied"})
            elapsed = time.perf_counter() - started
            self.assertLess(elapsed, 3.0)
            self.assertEqual(caught.exception.details["kind"], "response-timeout")
            self.assertIn("partialStdout", caught.exception.details)
            self.assertIsNotNone(session.process.poll())
        finally:
            session.close()

    def test_jsonl_invalid_timeout_is_rejected_before_launch(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self._child("import sys", timeout=value)

    def test_jsonl_child_closing_before_reply_is_infrastructure_failure(self):
        session = self._child("import sys; sys.stdin.readline(); sys.exit(0)")
        try:
            with self.assertRaises(lab.performance.SessionInfrastructureError) as caught:
                session.send({"request": "closed"})
            self.assertEqual(caught.exception.details["kind"], "process-closed-before-response")
        finally:
            session.close()

    def test_jsonl_malformed_response_is_distinct_from_timeout(self):
        session = self._child("import sys; sys.stdin.readline(); print('{bad', flush=True)")
        try:
            with self.assertRaises(lab.performance.SessionInfrastructureError) as caught:
                session.send({"request": "malformed"})
            self.assertEqual(caught.exception.details["kind"], "malformed-json")
            self.assertIn("rawResponse", caught.exception.details)
        finally:
            session.close()

    def test_jsonl_successful_session_reuse_remains_supported(self):
        session = self._child(
            "import sys, json; "
            "[print(json.dumps({'outcome': 'ok'}), flush=True) for line in sys.stdin]"
        )
        try:
            first, _ = session.send({"request": 1})
            second, _ = session.send({"request": 2})
            self.assertEqual(first, {"outcome": "ok"})
            self.assertEqual(second, {"outcome": "ok"})
        finally:
            session.close()

    def test_first_native_slice_remains_planned_only(self):
        manifest = lab.load_manifest()
        self.assertEqual(manifest["firstVerticalSlice"]["status"], "planned-not-implemented")
        self.assertIn("stable semantic IDs", manifest["firstVerticalSlice"]["requiredA13Facts"])


if __name__ == "__main__":
    unittest.main()
