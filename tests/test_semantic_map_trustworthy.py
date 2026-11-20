#!/usr/bin/env python3
"""
tests/test_semantic_map_trustworthy.py — Trustworthy Semantic Map, Living Spec & Multi-Agent Tests

Verifies Slice 2 & Slice 3 fixes from PEP-AG-20261120-02:
1. Rejection of nonexistent tests in living specifications.
2. Epistemic authority: compiler unavailability or failure never reports VALID.
3. Spec schema validation and duplicate requirement ID rejection.
4. Epistemic requirement states (UNIMPLEMENTED, TEST_MISSING, IMPLEMENTED, VERIFIED).
5. Mechanical repair safety:
   - No automatic resolution of ambiguous typos.
   - Rejection on stale revision hash or byte mismatch.
   - Rollback and non-SUCCESS on candidate compiler failure.
6. Context packet includes full target implementation, explicit omissions, and token budgeting.
7. Symmetric multi-agent conflict detection (bidirectional, modified/deleted, callers, line shifts).
"""

import copy
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pep_semantic_map import SemanticMap


class TrustworthySemanticMapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.td = pathlib.Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_nonexistent_tests_rejected_in_living_spec(self):
        """Living spec referencing nonexistent test must be marked INVALID."""
        pep_src = self.td / "sample.pep"
        pep_src.write_text("fn sample_add(a: Int, b: Int) -> Int {\n  return a + b\n}\n", encoding="utf-8")
        
        spec_file = self.td / "sample.spec.json"
        spec_data = {
            "specVersion": "1.0.0",
            "title": "Sample Module",
            "requirements": [
                {
                    "id": "REQ-SAMPLE-001",
                    "title": "Addition",
                    "symbols": ["sample_add"],
                    "tests": ["tests/test_nonexistent_file.py::test_missing_method"]
                }
            ]
        }
        spec_file.write_text(json.dumps(spec_data, indent=2), encoding="utf-8")

        smap = SemanticMap(pep_src, spec_file)
        report = smap.verify_specification()
        self.assertEqual(report["status"], "INVALID")
        self.assertTrue(len(report["nonexistentTests"]) > 0)
        self.assertEqual(report["nonexistentTests"][0]["requirement"], "REQ-SAMPLE-001")

    def test_test_references_do_not_verify_requirements(self):
        source = self.td / "sample.pep"
        source.write_text("fn sample() -> Int { return 1 }\n", encoding="utf-8")
        oracle = self.td / "test_oracle.py"
        oracle.write_text("def test_sample():\n    assert False\n", encoding="utf-8")
        spec_file = self.td / "sample.spec.json"

        for references in ([], [f"{oracle}::test_sample"]):
            with self.subTest(references=references):
                spec_file.write_text(json.dumps({"requirements": [{
                    "id": "REQ-SAMPLE",
                    "symbols": ["sample"],
                    "tests": references,
                }]}), encoding="utf-8")
                report = SemanticMap(source, spec_file).verify_specification()
                self.assertEqual(report["status"], "VALID")
                self.assertEqual(report["testedRequirements"], 0)
                self.assertEqual(report["verifiedRequirements"], 0)
                self.assertEqual(report["requirementsWithTestReferences"], len(references))
                self.assertEqual(report["matrix"][0]["status"], "IMPLEMENTED")
                self.assertFalse(report["matrix"][0]["verified"])

    def test_compiler_unavailability_never_reports_valid(self):
        """When compiler check is not valid, spec verification must not report VALID."""
        pep_src = self.td / "broken_syntax.pep"
        pep_src.write_text("fn broken( { invalid syntax\n", encoding="utf-8")
        
        spec_file = self.td / "broken.spec.json"
        spec_data = {
            "specVersion": "1.0.0",
            "title": "Broken Spec",
            "requirements": [
                {
                    "id": "REQ-001",
                    "title": "Broken",
                    "symbols": ["broken"],
                    "tests": []
                }
            ]
        }
        spec_file.write_text(json.dumps(spec_data, indent=2), encoding="utf-8")

        smap = SemanticMap(pep_src, spec_file)
        self.assertNotEqual(smap.epistemic_status, "CHECKED")
        report = smap.verify_specification()
        self.assertNotEqual(report["status"], "VALID")
        self.assertIn(report["status"], ("INVALID", "UNAVAILABLE"))

    def test_duplicate_requirement_ids_detected(self):
        """Specs with duplicate requirement IDs must be flagged as schema errors."""
        pep_src = self.td / "dup.pep"
        pep_src.write_text("fn a() -> Int { return 1 }\n", encoding="utf-8")
        spec_file = self.td / "dup.spec.json"
        spec_data = {
            "specVersion": "1.0.0",
            "title": "Duplicate ID Spec",
            "requirements": [
                {"id": "REQ-DUP-001", "title": "First", "symbols": ["a"], "tests": []},
                {"id": "REQ-DUP-001", "title": "Duplicate", "symbols": ["a"], "tests": []}
            ]
        }
        spec_file.write_text(json.dumps(spec_data, indent=2), encoding="utf-8")

        smap = SemanticMap(pep_src, spec_file)
        report = smap.verify_specification()
        self.assertEqual(report["status"], "INVALID")
        self.assertTrue(any("Duplicate requirement ID" in err for err in report["schemaErrors"]))

    def test_repair_rejects_ambiguous_identifiers(self):
        """Repair planner must never automatically pick arbitrary first candidate for ambiguous typos."""
        pep_src = self.td / "ambig.pep"
        # Two in-scope symbols start with 'calc_'
        pep_src.write_text(
            "fn calc_fast(x: Int) -> Int { return x }\n"
            "fn calc_slow(x: Int) -> Int { return x }\n"
            "fn run() -> Int { return calc_item(1) }\n",
            encoding="utf-8"
        )
        smap = SemanticMap(pep_src)
        diag = {
            "code": "PEP_UNBOUND_NAME",
            "message": "Unbound identifier 'calc_item'",
            "at": {"lo": 90, "hi": 99}
        }
        plan = smap.generate_repair_plan(diag)
        if plan is not None:
            # Must NOT be SAFE_AUTOMATIC with an arbitrary single replacement!
            self.assertNotEqual(plan.get("safety"), "SAFE_AUTOMATIC")
            self.assertIsNone(plan.get("replacement"))

    def test_repair_rollback_on_compiler_failure(self):
        """Applying a repair that breaks compilation must rollback original source and return failure."""
        pep_src = self.td / "rollback.pep"
        initial_content = "fn main() -> Int { return 0 }\n"
        pep_src.write_text(initial_content, encoding="utf-8")
        smap = SemanticMap(pep_src)

        # Forge a repair plan that introduces invalid syntax
        bad_plan = {
            "repairId": "REPAIR-BAD",
            "diagnosticCode": "PEP_TEST",
            "targetSpan": {"lo": 0, "hi": 2},
            "expectedSourceHash": smap.source_hash,
            "expectedOriginalBytes": "fn",
            "replacement": "INVALID_TOKEN %%$#@"
        }
        res = smap.apply_repair(bad_plan)
        self.assertNotEqual(res["status"], "SUCCESS")
        self.assertTrue(res.get("reverted", False))
        # Ensure file content was preserved
        self.assertEqual(pep_src.read_text(encoding="utf-8"), initial_content)

    def test_repair_rejects_stale_revision(self):
        """Repair must reject if source hash does not match expectedSourceHash."""
        pep_src = self.td / "stale.pep"
        pep_src.write_text("fn main() -> Int { return 0 }\n", encoding="utf-8")
        smap = SemanticMap(pep_src)

        stale_plan = {
            "repairId": "REPAIR-STALE",
            "targetSpan": {"lo": 0, "hi": 2},
            "expectedSourceHash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
            "expectedOriginalBytes": "fn",
            "replacement": "let"
        }
        res = smap.apply_repair(stale_plan)
        self.assertEqual(res["status"], "REJECTED_STALE_REVISION")

    def test_context_packet_includes_target_implementation(self):
        """Context packet must include the actual implementation code, not just signature."""
        smap = SemanticMap(ROOT / "examples" / "agent_calculator.pep", ROOT / "examples" / "agent_calculator.spec.json")
        packet = smap.get_context_packet("clamp", max_tokens=2000)
        self.assertIn("implementation", packet)
        self.assertIn("if val <= min_val", packet["implementation"])
        self.assertIn("## Target Implementation", packet["renderedMarkdown"])

    def test_symmetric_conflict_detection_order_independence(self):
        """detect_semantic_conflicts(base, A, B) MUST equal detect_semantic_conflicts(base, B, A)."""
        base_src = self.td / "base.pep"
        base_src.write_text(
            "fn helper(x: Int) -> Int { return x + 1 }\n"
            "fn caller() -> Int { return helper(10) }\n",
            encoding="utf-8"
        )
        base_map = SemanticMap(base_src)

        # Branch A: modifies helper's signature
        branch_a = copy.deepcopy(base_map)
        branch_a.symbols["helper"]["params"].append({"name": "extra", "type": "Int"})

        # Branch B: introduces a new caller of helper assuming original signature
        branch_b = copy.deepcopy(base_map)
        branch_b.symbols["new_caller"] = {
            "kind": "function", "name": "new_caller", "params": [], "returns": "Int"
        }
        branch_b.call_graph["new_caller"] = {"helper"}
        branch_b.caller_graph["helper"].add("new_caller")

        # Direction 1: (base, A, B)
        res_ab = SemanticMap.detect_semantic_conflicts(base_map, branch_a, branch_b)
        # Direction 2: (base, B, A)
        res_ba = SemanticMap.detect_semantic_conflicts(base_map, branch_b, branch_a)

        self.assertTrue(res_ab["hasConflicts"])
        self.assertTrue(res_ba["hasConflicts"])
        self.assertEqual(res_ab["conflictCount"], res_ba["conflictCount"])
        self.assertEqual(
            {c["type"] for c in res_ab["conflicts"]},
            {c["type"] for c in res_ba["conflicts"]}
        )

    def test_deleted_symbol_conflicts_detected(self):
        """Deleting a symbol in one branch while another branch calls or modifies it is detected."""
        base_src = self.td / "base_del.pep"
        base_src.write_text(
            "fn to_be_deleted() -> Int { return 42 }\n"
            "fn other() -> Int { return 0 }\n",
            encoding="utf-8"
        )
        base_map = SemanticMap(base_src)

        # Branch A deletes to_be_deleted
        branch_a = copy.deepcopy(base_map)
        del branch_a.symbols["to_be_deleted"]

        # Branch B calls to_be_deleted
        branch_b = copy.deepcopy(base_map)
        branch_b.call_graph["other"] = {"to_be_deleted"}

        conflicts = SemanticMap.detect_semantic_conflicts(base_map, branch_a, branch_b)
        self.assertTrue(conflicts["hasConflicts"])
        types = [c["type"] for c in conflicts["conflicts"]]
        self.assertIn("CALL_TO_DELETED_SYMBOL", types)

    def test_line_shifts_do_not_cause_semantic_conflicts(self):
        """Harmless line or comment shifts must NOT be flagged as semantic conflicts."""
        base_src = self.td / "base_lines.pep"
        base_src.write_text("fn compute(x: Int) -> Int {\n  return x * 2\n}\n", encoding="utf-8")
        base_map = SemanticMap(base_src)

        # Branch A inserts comments above compute (changing its line/span)
        branch_a = copy.deepcopy(base_map)
        branch_a.symbols["compute"]["span"] = {"lo": 50, "hi": 90, "line": 5}

        # Branch B unchanged
        branch_b = copy.deepcopy(base_map)

        conflicts = SemanticMap.detect_semantic_conflicts(base_map, branch_a, branch_b)
        self.assertFalse(conflicts["hasConflicts"])


if __name__ == "__main__":
    unittest.main()
