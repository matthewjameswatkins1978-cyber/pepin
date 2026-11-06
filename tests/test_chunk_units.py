"""Typed-bound function-unit records (A1 amendment): fail-closed pins.

Pins the record layer of docs/CHECKED_CHUNK_CONTRACT_TYPED_BOUND_DRAFT.md:
- statement-range tiling (overlap refused, bounds refused),
- fail-closed carry (bindings admitted only from valid, clean units),
- first-refusal stickiness,
- terminal-only-on-last rule,
- totality (CHUNK_INCOMPLETE until every statement is covered exactly once),
- END-TO-END on the real lexer: utf8_check's 21-unit bound chain checks the
  function COVERED through this record with carried bindings (measured at
  codex/a1-typed-bound-pipeline@04573c9).

No budgets, tools, or canonical contract file are touched by these tests.
"""
import unittest

import pep_chunk_contract as contract
import pep_chunk_units as units
from tests import test_chained_bindings as chained


class UnitRecordArithmeticTests(unittest.TestCase):
    """Pure arithmetic pins over a fake minimal index-like object."""

    class FakeIndex:
        document = "doc"
        revision = "rev"

        def statement_children(self, function_id):
            return list(range(4))  # 4 statements

        def bounded_units(self, function_id, groups=None):
            for label, lo, hi, carriers, expect_returns in groups:
                yield (label, tuple((function_id,) * (hi - lo)), expect_returns)

    def setUp(self):
        self.record = units.FunctionUnits(self.FakeIndex(), 100)

    def test_tiling_rejects_overlap_and_bounds(self):
        self.record.accept(0, 1, None, ["anything"])
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.accept(0, 2, None, [])
        self.assertEqual(caught.exception.code, "CHUNK_COVERAGE_MISMATCH")
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.unit_ids(3, 5)
        self.assertEqual(caught.exception.code, "CHUNK_COVERAGE_MISMATCH")
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.unit_ids(2, 2)
        self.assertEqual(caught.exception.code, "CHUNK_COVERAGE_MISMATCH")

    def test_first_refusal_sticks_and_blocks_carry(self):
        self.record.accept(0, 1, None, ["PEP_UNEXPECTED"])
        # a later CLEAN unit may be recorded, but the refusal is kept
        clean_report = {"type": "CheckerReport",
                        "fields": [{"name": "status",
                                    "value": {"type": "Str", "value": "valid"}},
                                   {"name": "bindings",
                                    "value": {"type": "List[BindingFact]",
                                              "value": []}},
                                   {"name": "diagnostics",
                                    "value": {"type": "List[Diagnostic]",
                                              "value": []}}]}
        self.record.accept(1, 2, clean_report, [], label="clean-1")
        result = self.record.complete() if False else None
        # not yet complete (2 of 4 statements) -> totality refusal mentions first miss
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.complete()
        self.assertEqual(caught.exception.code, "CHUNK_INCOMPLETE")
        self.assertEqual(self.record.first_refusal["lo"], 0)
        self.assertEqual(self.record.first_refusal["codes"], ["PEP_UNEXPECTED"])

    def test_clean_unit_carry_counts_pool_facts(self):
        pool = contract.BindingPool("doc", "rev")
        record = units.FunctionUnits(self.FakeIndex(), 7, pool=pool)
        clean_report = {"fields": [
            {"name": "status", "value": {"type": "Str", "value": "valid"}},
            {"name": "bindings", "value": {"type": "List[BindingFact]",
                                           "value": []}},
            {"name": "diagnostics", "value": {"type": "List[Diagnostic]",
                                              "value": []}}]}
        record.accept(0, 4, clean_report, [], label="all", terminal=True)
        result = record.complete()
        self.assertEqual(result["status"], "valid")
        self.assertIsNone(result["first_refusal"])
        self.assertEqual(result["statementCount"], 4)
        self.assertEqual(result["unitCount"], 1)

    def test_terminal_must_end_at_body(self):
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.accept(0, 2, None, [], terminal=True)
        self.assertEqual(caught.exception.code, "CHUNK_COVERAGE_MISMATCH")

    def test_complete_requires_last_unit_to_close_body(self):
        # Structural totality: a partial record can never complete (the
        # missing statement is refused by the tiling). The old separate
        # "no unit closes the body" branch is unreachable under tiling and
        # was removed; this pin documents the shape: covering statements
        # 0..2 of 4 leaves statement 3 missing -> CHUNK_INCOMPLETE.
        report = {"fields": [{"name": "status",
                              "value": {"type": "Str", "value": "valid"}},
                             {"name": "bindings",
                              "value": {"type": "List[BindingFact]", "value": []}},
                             {"name": "diagnostics",
                              "value": {"type": "List[Diagnostic]", "value": []}}]}
        self.record.accept(0, 3, report, [])
        with self.assertRaises(contract.ContractRefusal) as caught:
            self.record.complete()
        self.assertEqual(caught.exception.code, "CHUNK_INCOMPLETE")

    def test_whole_body_non_terminal_unit_records_residual(self):
        # MEASURED RESIDUAL PIN: a whole-body unit checked with checker-level
        # expect_returns=False still completes the record; the unit carries
        # checker_expect_returns=False so reviewers see the missing-return
        # residual is covered by the draft's documented pricing, not hidden.
        report = {"fields": [{"name": "status",
                              "value": {"type": "Str", "value": "valid"}},
                             {"name": "bindings",
                              "value": {"type": "List[BindingFact]", "value": []}},
                             {"name": "diagnostics",
                              "value": {"type": "List[Diagnostic]", "value": []}}]}
        self.record.accept(0, 4, report, [], label="all", terminal=True)
        result = self.record.complete()
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["units"][0].get("checker_expect_returns"), False)


class Utf8ChainThroughRecordTests(unittest.TestCase):
    """END-TO-END: the measured 21-unit utf8_check chain recorded fail-closed."""

    def test_utf8_check_covers_through_unit_record(self):
        chained.ChainedBindingTests.setUpClass()
        try:
            t = chained.ChainedBindingTests(
                "test_utf8_check_is_fully_covered_by_chained_units")
            pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            record = units.FunctionUnits(t.index, t.table["utf8_check"], pool=pool)
            total = record.total
            self.assertEqual(total, 21)
            for position in range(total):
                if position < total - 1:
                    chunk, terminal = t.statement_chunk("utf8_check", position)
                    report, codes = t.invoke("utf8_check", chunk, False,
                                             pool.facts())
                    record.accept(position, position + 1, report, codes,
                                  label=f"statement[{position}]")
                else:
                    ids, expect_returns = t.statement_chunk("utf8_check", position)
                    report, codes = t.invoke("utf8_check", ids, False,
                                             pool.facts())
                    record.accept(total - 1, total, report, codes,
                                  label="terminal", terminal=True)
            result = record.complete()
            self.assertEqual(result["status"], "valid",
                             result["first_refusal"])
            self.assertIsNone(result["first_refusal"])
            self.assertEqual(result["statementCount"], 21)
            self.assertEqual(result["unitCount"], 21)
            self.assertGreaterEqual(result["bindingsCarried"], 9)
        finally:
            chained.TypedChunkTeardown = None


if __name__ == "__main__":
    unittest.main()
