import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pep_semantic_map import SemanticMap


class SemanticMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_pep = ROOT / "examples" / "agent_calculator.pep"
        cls.spec_json = ROOT / "examples" / "agent_calculator.spec.json"
        cls.smap = SemanticMap(cls.source_pep, cls.spec_json)

    def test_symbols_and_call_graph_extracted(self):
        self.assertIn("factorial", self.smap.symbols)
        self.assertIn("power", self.smap.symbols)
        self.assertIn("clamp", self.smap.symbols)
        self.assertIn("calculate_clamped_factorial", self.smap.symbols)
        self.assertIn("main", self.smap.symbols)

        # Call graph: calculate_clamped_factorial calls factorial and clamp
        callees = self.smap.call_graph.get("calculate_clamped_factorial", set())
        self.assertIn("factorial", callees)
        self.assertIn("clamp", callees)

        # Caller graph: factorial is called by calculate_clamped_factorial
        callers = self.smap.caller_graph.get("factorial", set())
        self.assertIn("calculate_clamped_factorial", callers)

    def test_living_specification_verification(self):
        res = self.smap.verify_specification()
        self.assertEqual(res["status"], "VALID")
        self.assertEqual(res["totalRequirements"], 4)
        self.assertEqual(res["implementedRequirements"], 4)
        self.assertEqual(len(res["missingSymbols"]), 0)

    def test_affected_tests_transitive_calculation(self):
        # When 'clamp' is modified:
        # direct callers: calculate_clamped_factorial
        # affected tests should include tests for clamp AND tests for calculate_clamped_factorial!
        affected = self.smap.get_affected_tests(["clamp"])
        impacted_syms = affected["transitiveImpactedSymbols"]
        self.assertIn("clamp", impacted_syms)
        self.assertIn("calculate_clamped_factorial", impacted_syms)

        affected_test_names = [t["test"] for t in affected["affectedTests"]]
        # Direct tests
        self.assertTrue(any("test_clamp" in t for t in affected_test_names))
        # Transitive tests
        self.assertTrue(any("test_calculate_clamped_factorial" in t for t in affected_test_names))

    def test_dependency_complete_context_packet(self):
        packet = self.smap.get_context_packet("calculate_clamped_factorial", max_tokens=2000)
        self.assertEqual(packet["targetSymbol"], "calculate_clamped_factorial")
        self.assertIn("factorial", str(packet["calleeSignatures"]))
        self.assertIn("clamp", str(packet["calleeSignatures"]))
        self.assertIn("REQ-CALC-004", str(packet["linkedRequirements"]))
        self.assertIn("tests/test_agent_calculator.py", str(packet["linkedTests"]))

        # Verify markdown rendering
        md = packet["renderedMarkdown"]
        self.assertIn("# Context Packet: `calculate_clamped_factorial`", md)
        self.assertIn("## Callee Dependencies", md)
        self.assertIn("## Linked Requirements", md)
        self.assertFalse(packet["budgetExceeded"])

    def test_mechanical_repair_plan_generation(self):
        # Diagnostic: hole with expected type Int
        diag = {
            "code": "PEP_HOLE",
            "message": "Found typed hole with expected type Int",
            "expected": "Int",
            "at": {"lo": 50, "hi": 51, "line": 3, "column": 10}
        }
        plan = self.smap.generate_repair_plan(diag)
        self.assertIsNotNone(plan)
        self.assertEqual(plan["diagnosticCode"], "PEP_HOLE")
        self.assertEqual(plan["safety"], "SUGGESTED_CHOICE")

        # Diagnostic: typo in unbound variable
        typo_diag = {
            "code": "PEP_UNBOUND_NAME",
            "message": "Unbound identifier 'factorial_x'",
            "at": {"lo": 120, "hi": 131, "line": 8, "column": 5}
        }
        typo_plan = self.smap.generate_repair_plan(typo_diag)
        self.assertIsNotNone(typo_plan)
        self.assertEqual(typo_plan["safety"], "SAFE_AUTOMATIC")
        self.assertEqual(typo_plan["replacement"], "factorial")

    def test_multi_agent_semantic_conflict_detection(self):
        # Simulate base
        base_map = self.smap

        # Simulate Branch A: changes signature of clamp(val, min_val, max_val, mode: Int)
        import copy
        branch_a = copy.deepcopy(base_map)
        branch_a.symbols["clamp"]["params"].append({"name": "mode", "type": "Int"})

        # Simulate Branch B: adds a new function 'safe_eval' that calls 'clamp(10, 0, 100)'
        branch_b = copy.deepcopy(base_map)
        branch_b.symbols["safe_eval"] = {
            "kind": "function", "name": "safe_eval", "params": [], "returns": "Int"
        }
        branch_b.call_graph["safe_eval"] = {"clamp"}
        branch_b.caller_graph["clamp"].add("safe_eval")

        # Compare: Git merge would see two completely different lines (text disjoint)
        # But semantic conflict analysis detects that Branch B calls clamp assuming base signature,
        # while Branch A modified clamp's signature!
        conflicts = SemanticMap.detect_semantic_conflicts(base_map, branch_a, branch_b)
        self.assertTrue(conflicts["hasConflicts"])
        self.assertEqual(conflicts["conflictCount"], 1)
        self.assertEqual(conflicts["conflicts"][0]["type"], "SEMANTIC_SIGNATURE_COLLISION")
        self.assertEqual(conflicts["conflicts"][0]["symbol"], "clamp")


if __name__ == "__main__":
    unittest.main()
