"""Chained binding facts: a later statement checks valid given earlier ones.

The chunk entry point ``analyze_chunk_typed_bound`` accepts externally
supplied BindingFacts. Scope keys are source-anchored, so a binding derived
while checking one unit matches the same source construct in another, and a
long function can be covered statement by statement without re-sending its
prefix as source.

Binding ids are NOT portable: every chunk numbers its bindings from 2000000,
so pooling raw facts aliases different bindings to one id and a lookup for
``width`` can resolve to ``first``. ``BindingPool`` renumbers on admission, and
that is the difference between 14/21 and 21/21 statements on ``utf8_check``.
"""
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import parse_target
from tests import test_chunk_typed as typed_probe
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, resolved_sig_value)
from tests.test_chunk_typed import host_builtins


class ChainedBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = typed_probe.TypedChunkTests(
            "test_make_token_body_only_stays_valid_with_facts")
        typed_probe.TypedChunkTests.setUpClass()
        cls.session = typed_probe.TypedChunkTests.session
        cls.revision = typed_probe.TypedChunkTests.tool_revision
        cls.raw = (typed_probe.ROOT / "examples" / "pep_lexer.pep").read_bytes()
        bundle_text = "\n".join(p.read_text(encoding="utf-8")
                                for p in pep_c23.SOURCES)
        bundle = cls.session.send({"schemaVersion": 3, "op": "open",
                                   "source": bundle_text, "name": "pep-c23",
                                   "metadataOnly": True})
        cls.tool_document = bundle["document"]
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "chain", "bytes": list(cls.raw)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.parsed = parse_target(cls.session, cls.raw, target, cls.revision)
        cls.nodes = fields_map(cls.parsed)["nodes"]["value"]
        cls.index = contract.DocumentIndex.from_parsed(cls.parsed)
        cls.sigs = fetch_all_sigs(cls.session, cls.parsed, cls.revision, cls.sem)
        decl_roots = [int(nval(n, "id")) for n in cls.nodes
                      if str(nval(n, "parentId")) == "-1"
                      and nval(n, "kind") in ("record_declaration",
                                              "union_declaration")]
        cls.facts = []
        for root in decl_roots:
            cls.facts.extend(cls.harness.type_facts(cls.parsed, cls.sem,
                                                    cls.index.subtree(root)))
        cls.host = host_builtins(target["document"], target["revision"])
        cls.table = {str(nval(n, "text")): int(nval(n, "id")) for n in cls.nodes
                     if nval(n, "kind") == "function"
                     and str(nval(n, "parentId")) == "-1"}
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "validate", "bytes": []})
        vector = [pep_c23.parser_progress(sample["document"], sample["revision"]),
                  {"type": "List[CheckedFunction]", "value": []},
                  {"type": "List[ResolvedSignature]", "value": []},
                  {"type": "List[ResolvedTypeDecl]", "value": []},
                  {"type": "List[BindingFact]", "value": []},
                  {"type": "Bool", "value": True}]
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": "bound-chunk",
                          "document": cls.tool_document, "revision": cls.revision,
                          "function": "analyze_chunk_typed_bound"})
        registration = cls.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
             "tool": "bound-chunk", "document": cls.tool_document,
             "revision": cls.revision,
             "testVectors": [{"arguments": vector,
                              "expect": pep_c23.checker_report(
                                  sample["document"], sample["revision"]),
                              "semanticTarget": {"document": sample["document"],
                                                 "revision": sample["revision"],
                                                 "entryFunctions": []}}]})
        assert registration.get("outcome") == "ok", registration.get("error")
        cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": "bound-chunk",
                          "document": cls.tool_document,
                          "revision": cls.revision})

    @classmethod
    def tearDownClass(cls):
        typed_probe.TypedChunkTests.tearDownClass()

    def statement_chunk(self, entry, position):
        for label, ids, terminal in self.index.bounded_units(
                self.table[entry],
                groups=[("one", position, position + 1, (), False)]):
            if label == "one":
                return ids, terminal
        raise AssertionError(position)

    def invoke(self, entry, chunk_ids, expect_returns, bindings):
        host_fns, host_sigs, host_types = self.host
        ext = [s for s in self.sigs if s["name"] != entry]
        allowed = self.index.fact_closure(chunk_ids, {s["name"] for s in ext})
        ext = [s for s in ext if s["name"] in allowed]
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "bound-chunk",
             "arguments": [
                 self.harness.sliced(self.parsed, chunk_ids),
                 {"type": "List[CheckedFunction]",
                  "value": [checked_fn_value(s) for s in ext] + host_fns},
                 {"type": "List[ResolvedSignature]",
                  "value": [resolved_sig_value(s) for s in ext] + host_sigs},
                 {"type": "List[ResolvedTypeDecl]", "value": self.facts + host_types},
                 {"type": "List[BindingFact]", "value": bindings},
                 {"type": "Bool", "value": expect_returns}],
             "semanticTarget": self.sem})
        if response.get("outcome") != "ok":
            return None, [(response.get("error") or {}).get("code")]
        report = fields_map(response["result"])
        codes = [fields_map(d)["code"]["value"]
                 for d in report["diagnostics"]["value"]]
        return report, codes

    def chain(self, entry, pool=None):
        carried = pool if pool is not None else contract.BindingPool()
        statements = self.index.statement_children(self.table[entry])
        accepted, rejected = 0, []
        for position in range(len(statements)):
            chunk, terminal = self.statement_chunk(entry, position)
            report, codes = self.invoke(entry, chunk, terminal, carried.facts())
            if report is not None and report["status"]["value"] == "valid" and not codes:
                accepted += 1
                carried.add(report["bindings"]["value"])
            else:
                status = report["status"]["value"] if report else codes
                rejected.append((position, status, sorted(set(codes))[:2]))
        return accepted, len(statements), rejected

    def test_utf8_check_is_fully_covered_by_chained_units(self):
        # 21 of 21 statements check valid, against 5 without binding facts.
        accepted, total, rejected = self.chain("utf8_check")
        self.assertEqual(total, 21)
        self.assertEqual(accepted, 21, rejected)

    def test_raw_pooling_aliases_bindings_and_loses_coverage(self):
        # Every chunk numbers bindings from 2000000, so concatenating raw
        # facts without renumbering collapses distinct bindings onto one id.
        class RawPool:
            def __init__(self):
                self.items = []

            def add(self, bindings):
                self.items.extend(bindings)

            def facts(self):
                return self.items

        accepted, _total, _rejected = self.chain("utf8_check", RawPool())
        self.assertLess(accepted, 21)
        self.assertEqual(accepted, 7)

    def test_pool_renumbers_and_dedupes(self):
        pool = contract.BindingPool()
        self.assertEqual(pool.add([]), 0)
        fact = {"type": "BindingFact", "fields": [
            {"name": "semanticId", "value": {"type": "Int", "value": "2000003"}},
            {"name": "syntaxId", "value": {"type": "Int", "value": "7"}},
            {"name": "name", "value": {"type": "Str", "value": "width"}},
            {"name": "ownerFunctionId", "value": {"type": "Int", "value": "100000"}},
            {"name": "scopeId", "value": {"type": "Int", "value": "100000"}},
            {"name": "visibleFrom", "value": {"type": "Int", "value": "1346"}},
            {"name": "mutable", "value": {"type": "Bool", "value": True}},
            {"name": "typeName", "value": {"type": "Str", "value": "Int"}}]}
        self.assertEqual(pool.add([fact]), 1)
        self.assertEqual(pool.add([fact]), 0)  # deduped by identity
        admitted = pool.facts()[0]
        semantic = [f for f in admitted["fields"] if f["name"] == "semanticId"][0]
        self.assertEqual(semantic["value"]["value"], str(contract.BindingPool.BASE))


if __name__ == "__main__":
    unittest.main()
