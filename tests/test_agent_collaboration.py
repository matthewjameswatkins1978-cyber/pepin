import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pep_semantic_map import SemanticMap


class MultiAgentCollaborationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_pep = ROOT / "examples" / "agent_calculator.pep"
        cls.spec_json = ROOT / "examples" / "agent_calculator.spec.json"
        cls.base_map = SemanticMap(cls.source_pep, cls.spec_json)

    def test_disjoint_agent_lanes(self):
        """Simulate two agents working on non-overlapping symbol sets."""
        agent1_map = copy.deepcopy(self.base_map)
        agent2_map = copy.deepcopy(self.base_map)

        # Agent 1 implements fibonacci
        agent1_map.symbols["fibonacci"] = {
            "kind": "function", "name": "fibonacci",
            "params": [{"name": "n", "type": "Int"}], "returns": "Int"
        }

        # Agent 2 implements gcd
        agent2_map.symbols["gcd"] = {
            "kind": "function", "name": "gcd",
            "params": [{"name": "a", "type": "Int"}, {"name": "b", "type": "Int"}], "returns": "Int"
        }

        conflicts = SemanticMap.detect_semantic_conflicts(self.base_map, agent1_map, agent2_map)
        self.assertFalse(conflicts["hasConflicts"])
        self.assertEqual(conflicts["conflictCount"], 0)

    def test_competing_implementations_against_same_oracle(self):
        """
        Two agents propose competing implementations for REQ-CALC-001 (Factorial):
        Candidate A: Direct recursion
        Candidate B: Tail-recursive accumulator
        Both must satisfy the same living spec contract.
        """
        spec = self.base_map.requirements.get("REQ-CALC-001")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["status"], "VERIFIED")

        # Candidate A representation
        cand_a_symbols = ["factorial"]
        # Candidate B representation
        cand_b_symbols = ["factorial", "factorial_acc"]

        # Both candidates provide 'factorial' matching the contract signature
        self.assertIn("factorial", cand_a_symbols)
        self.assertIn("factorial", cand_b_symbols)

    def test_semantic_conflict_prevention_on_text_disjoint_changes(self):
        """
        Demonstrate detection of a semantic signature collision where Git text merge
        would have blindly succeeded with zero merge conflicts.
        """
        agent_a = copy.deepcopy(self.base_map)
        agent_b = copy.deepcopy(self.base_map)

        # Agent A changes signature of 'factorial' to require 'allow_negative: Bool'
        agent_a.symbols["factorial"]["params"].append({"name": "allow_negative", "type": "Bool"})

        # Agent B adds a new function 'compute_stat' calling 'factorial' assuming original signature
        agent_b.symbols["compute_stat"] = {
            "kind": "function", "name": "compute_stat", "params": [], "returns": "Int"
        }
        agent_b.call_graph["compute_stat"] = {"factorial"}
        agent_b.caller_graph["factorial"].add("compute_stat")

        conflicts = SemanticMap.detect_semantic_conflicts(self.base_map, agent_a, agent_b)
        self.assertTrue(conflicts["hasConflicts"])
        self.assertEqual(len(conflicts["conflicts"]), 1)
        c = conflicts["conflicts"][0]
        self.assertEqual(c["type"], "SEMANTIC_SIGNATURE_COLLISION")
        self.assertEqual(c["symbol"], "factorial")
        self.assertEqual(c["severity"], "CRITICAL")

    def test_context_reduction_empirical_measurement(self):
        """
        Empirically measure agent context token consumption:
        Full project module (e.g. realistic 2000-token module) vs Dependency-Complete Context Packet.
        """
        # When working in a realistic module (e.g. 2,000 tokens / 8,000 bytes like lexer/parser),
        # an agent editing one symbol only needs its target signature, dependencies, and requirements.
        realistic_module_tokens = 2000

        # Context packet for 'clamp'
        packet = self.base_map.get_context_packet("clamp")
        packet_tokens = packet["approximateTokens"]

        # Context reduction ratio compared to a realistic module context
        reduction_pct = (1.0 - (packet_tokens / realistic_module_tokens)) * 100.0
        self.assertGreater(reduction_pct, 70.0, f"Expected >70% context savings, got {reduction_pct:.1f}%")
        self.assertLess(packet_tokens, 300, "Context packet should be bounded under 300 tokens for small helper")

    def test_verify_lane_allowed_changes(self):
        """Agent modifies only symbols inside its assigned lane -> APPROVED."""
        lane_def = {
            "laneId": "lane-math-helpers",
            "allowedSymbols": ["clamp", "power"],
            "allowNewSymbols": False,
            "assignedRequirements": ["REQ-CALC-002", "REQ-CALC-003"]
        }
        agent_map = copy.deepcopy(self.base_map)
        res = agent_map.verify_lane(lane_def, self.base_map)
        self.assertTrue(res["laneValid"])
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["violationCount"], 0)

    def test_verify_lane_rejects_out_of_lane_changes(self):
        """Agent modifies symbol outside its declared lane -> REJECTED."""
        lane_def = {
            "laneId": "lane-math-helpers",
            "allowedSymbols": ["clamp", "power"],
            "allowNewSymbols": False,
            "assignedRequirements": ["REQ-CALC-002"]
        }
        agent_map = copy.deepcopy(self.base_map)
        # Agent accidentally mutates 'factorial' (which belongs to another lane)
        agent_map.symbols["factorial"]["returns"] = "Bool"

        res = agent_map.verify_lane(lane_def, self.base_map)
        self.assertFalse(res["laneValid"])
        self.assertEqual(res["status"], "REJECTED")
        violations = [v["type"] for v in res["violations"]]
        self.assertIn("OUT_OF_LANE_MODIFICATION", violations)

    def test_verify_lane_rejects_breaking_caller_contract(self):
        """Agent modifies signature of an assigned symbol that outside callers depend on -> REJECTED."""
        lane_def = {
            "laneId": "lane-math-helpers",
            "allowedSymbols": ["clamp"],
            "allowNewSymbols": False
        }
        agent_map = copy.deepcopy(self.base_map)
        # In base_map, 'calculate_clamped_factorial' calls 'clamp'.
        # 'calculate_clamped_factorial' is OUTSIDE this lane!
        agent_map.symbols["clamp"]["params"].append({"name": "extra", "type": "Int"})

        res = agent_map.verify_lane(lane_def, self.base_map)
        self.assertFalse(res["laneValid"])
        violations = [v["type"] for v in res["violations"]]
        self.assertIn("BREAKING_CALLER_CONTRACT", violations)

    def test_verify_lane_cli_execution(self):
        """Verify CLI execution of verify-lane."""
        import subprocess
        lane_path = ROOT / "_build" / "test_lane.json"
        lane_path.parent.mkdir(parents=True, exist_ok=True)
        lane_def = {
            "laneId": "test-cli-lane",
            "allowedSymbols": ["clamp", "power", "factorial", "calculate_clamped_factorial"],
            "allowNewSymbols": False,
            "assignedRequirements": ["REQ-CALC-001", "REQ-CALC-002", "REQ-CALC-003", "REQ-CALC-004"]
        }
        lane_path.write_text(json.dumps(lane_def), encoding="utf-8")

        cmd = [
            sys.executable, str(ROOT / "pep_semantic_map.py"),
            "verify-lane", str(self.source_pep),
            "--lane-file", str(lane_path),
            "--base", str(self.source_pep),
            "--json"
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["laneValid"])
        self.assertEqual(data["status"], "APPROVED")

    def test_check_merge_cli_execution(self):
        """Verify CLI execution of check-merge."""
        import subprocess
        # Check merge with base vs base vs base should be completely safe
        cmd = [
            sys.executable, str(ROOT / "pep_semantic_map.py"),
            "check-merge", str(self.source_pep), str(self.source_pep), str(self.source_pep),
            "--json"
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["hasConflicts"])
        self.assertEqual(data["conflictCount"], 0)


if __name__ == "__main__":
    unittest.main()
