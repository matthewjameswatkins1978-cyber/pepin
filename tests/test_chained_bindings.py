"""Chained binding facts: a later statement checks valid given earlier ones.

The chunk entry point ``analyze_chunk_typed_bound`` accepts externally
supplied BindingFacts. Because scope keys are source-anchored, a binding
derived while checking one unit matches the same source construct in another,
so a long function can be covered statement by statement without re-sending its
prefix as source.

This pins the measured state rather than an aspiration: 14 of 21 statements of
`utf8_check` become valid by chaining, and the remainder still fail on
PEP_ASSIGN_IMMUTABLE because a collected binding for an assignment target
shadows the external mutable one.
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
        # Register the bound entry point, validated against an empty chunk.
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

    def chain(self, entry):
        carried, seen, accepted, rejected = [], set(), 0, []
        statements = self.index.statement_children(self.table[entry])
        for position in range(len(statements)):
            chunk, terminal = self.statement_chunk(entry, position)
            report, codes = self.invoke(entry, chunk, terminal, carried)
            if report is not None and report["status"]["value"] == "valid" and not codes:
                accepted += 1
                for binding in report["bindings"]["value"]:
                    fields = fields_map(binding)
                    key = (fields["name"]["value"],
                           str(fields["ownerFunctionId"]["value"]),
                           str(fields["scopeId"]["value"]),
                           str(fields["visibleFrom"]["value"]))
                    if key not in seen:
                        seen.add(key)
                        carried.append(binding)
            else:
                rejected.append((position, codes))
        return accepted, len(statements), rejected

    def test_chaining_covers_most_of_a_long_function(self):
        # Pinned measurement: 14 of 21 statements of utf8_check check valid by
        # chaining external binding facts, against 5 without them.
        accepted, total, rejected = self.chain("utf8_check")
        self.assertEqual(total, 21)
        self.assertEqual(accepted, 14, rejected)

    def test_remaining_failures_are_assignment_shadowing(self):
        # The seven that still fail do so for one reason, not budget: a
        # collected binding for the assignment target shadows the external
        # mutable one. That is the next thing to fix.
        _accepted, _total, rejected = self.chain("utf8_check")
        codes = {code for _position, codes in rejected for code in codes}
        self.assertEqual(codes, {"PEP_ASSIGN_IMMUTABLE"}, rejected)


if __name__ == "__main__":
    unittest.main()
