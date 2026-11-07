"""A1 sectional-emit translation proof (LUCY-20261107-014 transport slice).

A two-function program: `main` is force-checked as per-statement bound-chunks
(2 groups) and the merged host-side report is used to emit the `function-unit`
for the whole-`main` slice. The `let`-bound cross-chunk call
(`callee(41)`) can only lower through the checker's ResolvedCall facts, whose
syntaxIds live in per-group id spaces — so emission proves the host merge
translates group-space ids back into slice space.

Covers the merge machinery; the 11 fallible-operand and 8 known-target
refusals on real compiler-A source are emitter-semantics for A2's lane and
are deliberately NOT pinned here.
"""
import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import Session, parse_target
from pep_c23 import typed as T
from tests.chunk_helper import (fetch_all_sigs, fields_map, nval,
                                resolved_sig_value, checked_fn_value, slice_subtree)
from tests.test_chunk_typed import host_builtins
import sectional_check_a4 as base_probe
import sectional_emit_a4 as emit_probe

SRC = (b"fn callee(a: Int) -> Int { return a + 1 }\n"
       b"fn main() -> Int { let x = callee(41) return x }\n")


class SectionalEmitTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle_text = "\n".join(
            p.read_text(encoding="utf-8")
            for p in [pathlib.Path(x) for x in pep_c23.SOURCES])
        bundle = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle_text, "name": "pep-c23",
                                   "metadataOnly": True})
        cls.tool_revision = bundle["revision"]
        cls.tool_document = bundle["document"]
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "sectional-emit-proof",
                                   "bytes": list(SRC)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.target = target
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        emit_probe.register_parser_tools(cls.session, cls.tool_document,
                                         cls.tool_revision, sample)
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        refused = pep_c23.typed_record(
            "unsupported", (),
            "Pep C23 emission requires a top-level function named main")
        for tool, fn, args, expect in [
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp],
                 {"type": "List[ResolvedSignature]", "value": []}),
                ("pep-c23-unit", "emit_c23_function_unit",
                 [empty_pp, empty_checked, T("Int", 0)], refused)]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_register", "tool": tool,
                              "document": cls.tool_document,
                              "revision": cls.tool_revision, "function": fn})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": cls.tool_document,
                              "revision": cls.tool_revision,
                              "testVectors": [{"arguments": args, "expect": expect,
                                               "semanticTarget": {
                                                   "document": sample["document"],
                                                   "revision": sample["revision"],
                                                   "entryFunctions": []}}]})
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": cls.tool_document,
                              "revision": cls.tool_revision})
        vector = [empty_pp,
                  {"type": "List[CheckedFunction]", "value": []},
                  {"type": "List[ResolvedSignature]", "value": []},
                  {"type": "List[ResolvedTypeDecl]", "value": []},
                  {"type": "List[BindingFact]", "value": []},
                  {"type": "Bool", "value": True}]
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": "bound-chunk",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "function": "analyze_chunk_typed_bound"})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_validate", "tool": "bound-chunk",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision,
                          "testVectors": [{"arguments": vector,
                                           "expect": empty_checked,
                                           "semanticTarget": {
                                               "document": sample["document"],
                                               "revision": sample["revision"],
                                               "entryFunctions": []}}]})
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": "bound-chunk",
                          "document": cls.tool_document,
                          "revision": cls.tool_revision})

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def _emit_unit(self, sl, rep):
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2,
             "op": "tool_invoke", "tool": "pep-c23-unit",
             "arguments": [sl, rep, T("Int", 0)], "semanticTarget": self.sem})
        self.assertEqual(response.get("outcome"), "ok", response)
        return emit_probe.emission_of(response)

    def test_chain_merged_report_emits_cross_chunk_call(self):
        parsed = parse_target(self.session, SRC, self.target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, self.sem)
        host = host_builtins(self.target["document"], self.target["revision"])
        index = contract.DocumentIndex.from_parsed(parsed)
        fns = {nval(n, "text"): n for n in nodes
               if nval(n, "kind") == "function"
               and str(nval(n, "parentId")) == "-1"}
        # callee checks whole (leaf, single report)
        fn = fns["callee"]
        ids = [int(nval(n, "id")) for n in slice_subtree(nodes, nval(fn, "id"))]
        raw, codes, _ = emit_probe.raw_check_chunk(
            self.session, self.sem, parsed, index, sigs, host, ids, True, [],
            "callee")
        self.assertIsNotNone(raw)
        self.assertEqual(codes, [])
        status, _, parts = self._emit_unit(base_probe.sliced(parsed, ids), raw)
        self.assertEqual(status, "emitted")
        # main is FORCE-chained per statement, then merged host-side
        fn = fns["main"]
        ids = [int(nval(n, "id")) for n in slice_subtree(nodes, nval(fn, "id"))]
        sl = base_probe.sliced(parsed, ids)
        pool = contract.BindingPool(self.target["document"],
                                    self.target["revision"])
        parts_reports = []
        positions = index.statement_children(int(nval(fn, "id")))
        self.assertGreaterEqual(len(positions), 2)
        for pos in range(len(positions)):
            for label, cids, terminal in index.bounded_units(
                    int(nval(fn, "id")), groups=[("one", pos, pos + 1, (), False)]):
                if label != "one":
                    continue
                r2, c2, _ = emit_probe.raw_check_chunk(
                    self.session, self.sem, parsed, index, sigs, host,
                    list(cids), terminal, pool.facts(), "main")
                self.assertIsNotNone(r2, pos)
                self.assertEqual(c2, [], pos)
                parts_reports.append((list(cids), fields_map(r2)))
                pool.add(fields_map(r2)["bindings"]["value"])
        merged = emit_probe.merge_reports(
            sl, parts_reports, sorted(int(i) for i in ids), "main")
        status, diagnostic, out = self._emit_unit(sl, merged)
        self.assertEqual(status, "emitted", diagnostic)
        text = "".join(out)
        self.assertIn("pep_fn_main", text)
        # the let-bound cross-chunk call lowered through the translated facts
        self.assertIn("pep_fn_callee", text)


if __name__ == "__main__":
    unittest.main()
