"""Hostile pooled-carry gate for the typed-bound unit record (A3 condition 1).

BOOT-A3-007 endorsed Option A subject to this gate: the pooled carried-fact
path must refuse duplicates/aliases/foreign/omitted stamps per-group and must
not widen the pre-registered same-target forged-parameter admission.

These pins add to tests/test_chunk_units.py the HOSTILE half:
- a BindingFact whose document/revision do not match the record makes
  ``accept`` propagate the pool's explicit ValueError; the record state is
  unchanged (no entry appended, no binding carried);
- aliased/duplicate binding facts are pool-renumbered and deduped on
  admission (no id aliasing across units);
- a stamp-consistent forged fact that is USED by a checked unit SURFACES at
  the checker and is recorded as the record's first refusal - pooling never
  launders a forged fact into a green unit.

Uses the existing chained harness session (real checker), same document.
"""
import unittest

import pep_chunk_contract as contract
import pep_chunk_units as units
from tests import test_chained_bindings as chained
from tests.test_chained_bindings import stamped_binding


class PooledCarryHostileTests(unittest.TestCase):
    def test_foreign_document_stamp_propagates_and_state_unchanged(self):
        chained.ChainedBindingTests.setUpClass()
        try:
            t = chained.ChainedBindingTests(
                "test_utf8_check_is_fully_covered_by_chained_units")
            pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            record = units.FunctionUnits(t.index, t.table["utf8_check"], pool=pool)
            foreign = stamped_binding("first", type_name="Int", shape_name="Int",
                                      document="other-doc", revision="other-rev")
            with self.assertRaises(ValueError):
                record.accept(0, 1, {"status": {"type": "Str", "value": "valid"},
                                     "bindings": {"type": "List[BindingFact]",
                                                  "value": [foreign]},
                                     "diagnostics": {"type": "List[Diagnostic]",
                                                     "value": []}},
                              [], label="hostile-0")
            self.assertEqual(record.units, [])
            self.assertEqual(pool.facts(), [])
        finally:
            chained.TypedChunkTeardown = None

    def test_stale_revision_stamp_propagates(self):
        chained.ChainedBindingTests.setUpClass()
        try:
            t = chained.ChainedBindingTests(
                "test_utf8_check_is_fully_covered_by_chained_units")
            pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            record = units.FunctionUnits(t.index, t.table["utf8_check"], pool=pool)
            stale = stamped_binding("first", type_name="Int", shape_name="Int",
                                    document=t.sem["document"],
                                    revision="stale-" + t.sem["revision"])
            with self.assertRaises(ValueError):
                record.accept(0, 1, {"status": {"type": "Str", "value": "valid"},
                                     "bindings": {"type": "List[BindingFact]",
                                                  "value": [stale]},
                                     "diagnostics": {"type": "List[Diagnostic]",
                                                     "value": []}},
                              [], label="hostile-stale")
            self.assertEqual(record.units, [])
        finally:
            chained.TypedChunkTeardown = None

    def test_aliased_duplicates_renumbered_not_widened(self):
        chained.ChainedBindingTests.setUpClass()
        try:
            t = chained.ChainedBindingTests(
                "test_utf8_check_is_fully_covered_by_chained_units")
            pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            record = units.FunctionUnits(t.index, t.table["utf8_check"], pool=pool)
            fact_a = stamped_binding("first", semantic="2000001",
                                     document=t.sem["document"],
                                     revision=t.sem["revision"])
            fact_b = stamped_binding("width", semantic="2000001",
                                     document=t.sem["document"],
                                     revision=t.sem["revision"])
            clean = lambda extra: {"status": {"type": "Str", "value": "valid"},
                                   "bindings": {"type": "List[BindingFact]",
                                                "value": extra},
                                   "diagnostics": {"type": "List[Diagnostic]",
                                                   "value": []}}
            record.accept(0, 1, clean([fact_a]), [], label="u0")
            record.accept(1, 2, clean([fact_b]), [], label="u1")
            facts = pool.facts()
            ids = [f["fields"][0]["value"]["value"] for f in facts
                   if f["fields"][0]["name"] == "semanticId"]
            self.assertEqual(len(ids), len(set(ids)),
                             "pool must renumber aliased ids to distinct values")
            with self.assertRaises(contract.ContractRefusal) as caught:
                record.complete()  # 2 of 21 statements only
            self.assertEqual(caught.exception.code, "CHUNK_INCOMPLETE")
        finally:
            chained.TypedChunkTeardown = None

    def test_forged_pooled_param_used_downstream_surfaces_as_refusal(self):
        """A stamp-consistent forged fact (consistency-only residual) that is
        USED by the checked source must surface at the checker and be recorded
        as first refusal - never a green unit."""
        chained.ChainedBindingTests.setUpClass()
        try:
            t = chained.ChainedBindingTests(
                "test_utf8_check_is_fully_covered_by_chained_units")
            pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            record = units.FunctionUnits(t.index, t.table["utf8_check"], pool=pool)
            # PHASE 1: clean chain through group 2 - captures width's REAL
            # scope anchor from the checker's own report bindings.
            width_anchor = None
            for position in range(3):
                chunk, _term = t.statement_chunk("utf8_check", position)
                report, codes = t.invoke("utf8_check", chunk, False, pool.facts())
                record.accept(position, position + 1, report, codes,
                              label=f"clean[{position}]")
                if position == 2:
                    for fact in report["bindings"]["value"]:
                        fm = {f["name"]: f["value"] for f in fact["fields"]}
                        if fm["name"]["value"] == "width":
                            width_anchor = {
                                "owner": fm["ownerFunctionId"]["value"],
                                "scope": fm["scopeId"]["value"],
                                "visible": str(fm["visibleFrom"]["value"]),
                                "semantic": fm["semanticId"]["value"]}
            self.assertIsNotNone(width_anchor)
            # PHASE 2: fresh pool; inject forged width:Bool at the REAL anchor;
            # invoke the unit that USES width (statement 7, `if width == 0`).
            hostile_pool = contract.BindingPool(t.sem["document"], t.sem["revision"])
            forged = stamped_binding("width", type_name="Bool",
                                     shape_name="Bool",
                                     owner=str(width_anchor["owner"]),
                                     scope=str(width_anchor["scope"]),
                                     visible=width_anchor["visible"],
                                     semantic=str(width_anchor["semantic"]),
                                     document=t.sem["document"],
                                     revision=t.sem["revision"])
            outcome = hostile_pool.add([forged])
            self.assertLessEqual(outcome, 1)
            use_chunk, _term = t.statement_chunk("utf8_check", 7)
            report, codes = t.invoke("utf8_check", use_chunk, False,
                                     hostile_pool.facts())
            record.accept(7, 8, report, codes, label="forged-used-7")
            self.assertIsNotNone(record.first_refusal,
                                 "forged pooled fact must surface, not launder")
            self.assertEqual(record.first_refusal["lo"], 7)
        finally:
            chained.TypedChunkTeardown = None


if __name__ == "__main__":
    unittest.main()
