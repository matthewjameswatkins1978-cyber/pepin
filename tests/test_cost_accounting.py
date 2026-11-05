"""Read-only step accounting (Campaign K K2).

`pep_ocaml.ml` records, per `execute`, how many interpreter steps it consumed and
how many executions the process has performed. Both are additive observations in
`metrics`; neither can change a semantic result, a diagnostic, or a limit.

These pins exist so per-phase cost measurement stays reproducible from outside
(see `tests/probe_checker_phase_cost.py`) and so the accounting cannot silently
disappear or start lying. They deliberately do NOT pin absolute step numbers:
those move whenever the checker improves, and a moving fixture would force
re-measurement on every honest win. The pinned properties are the ones a correct
counter must have.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23
from pep_c23 import require, parse_target
from tests.chunk_helper import fields_map
from tests.probe_checker_phase_cost import CountingSession, measure, open_tools, recpad

NL = chr(10)


class StepAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = CountingSession()
        _, cls.tool_revision = open_tools(cls.session)

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def test_metrics_reports_the_observation_fields(self):
        metrics = self.session.metrics()
        self.assertIn("last_execute_steps", metrics)
        self.assertIn("execute_count", metrics)
        self.assertIsInstance(metrics["last_execute_steps"], int)
        self.assertIsInstance(metrics["execute_count"], int)

    def test_a_tool_invocation_increments_execute_count_and_reports_its_own_cost(self):
        before = self.session.metrics()["execute_count"]
        row = measure(self.session, self.tool_revision, "acct-small", recpad(1))
        after = self.session.metrics()
        self.assertEqual(row["status"], "valid")
        self.assertGreater(after["execute_count"], before)
        # The reported value is the cost of the LAST execute (the checker call),
        # bounded by the unchanged 100,000-step tool budget.
        self.assertEqual(after["last_execute_steps"], row["check_steps"])
        self.assertGreater(after["last_execute_steps"], 0)
        self.assertLessEqual(after["last_execute_steps"], 100000)

    def test_more_nodes_cost_more_steps_in_the_check_phase(self):
        # The ladder direction, not its absolute slope: per-node cost rises with
        # program size, which is the quadratic-scan signature rather than a
        # constant per-node price. Pinned as an inequality so a real improvement
        # in either component does not invalidate the observation.
        small = measure(self.session, self.tool_revision, "acct-k2", recpad(2))
        larger = measure(self.session, self.tool_revision, "acct-k4", recpad(4))
        self.assertEqual(small["status"], "valid")
        self.assertEqual(larger["status"], "valid")
        self.assertGreater(larger["nodes"], small["nodes"])
        self.assertGreater(larger["check_steps"], small["check_steps"])
        self.assertGreater(larger["check_steps"] / larger["nodes"],
                           small["check_steps"] / small["nodes"])

    def test_parser_phase_is_amortised_across_many_invocations(self):
        # The parser also costs steps, but each parser call is its own `execute`
        # with its own budget, so parse cost is spread over calls while the
        # checker's whole cost lands in ONE invocation. This is the structural
        # reason the checker budget binds first; pinned as an inequality.
        row = measure(self.session, self.tool_revision, "acct-parse", recpad(3))
        self.assertGreater(row["parse_calls"], 1)
        self.assertGreater(row["parse_steps"], 0)
        self.assertLess(row["parse_steps"] / row["parse_calls"], 100000)


if __name__ == "__main__":
    unittest.main()
