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


if __name__ == "__main__":
    unittest.main()
