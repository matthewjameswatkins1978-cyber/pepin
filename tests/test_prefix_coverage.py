"""Coverage of a function is limited by its *prefix* size, not unit size.

A later statement reads bindings introduced earlier, so any unit containing it
must re-include those statements as source. Once the prefix is over budget, the
tail of the function is unreachable by source slicing alone. Measured on
`utf8_check`, which has 21 top-level statements.
"""
import unittest

import pep_chunk_contract as contract
from pep_c23 import parse_target
from tests import test_chunk_typed as typed_probe
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, resolved_sig_value)
from tests.test_chunk_typed import host_builtins


class PrefixCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = typed_probe.TypedChunkTests(
            "test_make_token_body_only_stays_valid_with_facts")
        typed_probe.TypedChunkTests.setUpClass()
        cls.session = typed_probe.TypedChunkTests.session
        cls.tool_revision = typed_probe.TypedChunkTests.tool_revision
        cls.source = (typed_probe.ROOT / "examples" / "pep_lexer.pep").read_bytes()
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "prefix", "bytes": list(cls.source)})
        assert target.get("outcome") == "ok", target
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.parsed = parse_target(cls.session, cls.source, target,
                                  cls.tool_revision)
        cls.nodes = fields_map(cls.parsed)["nodes"]["value"]
        cls.index = contract.DocumentIndex.from_parsed(cls.parsed)
        cls.sigs = fetch_all_sigs(cls.session, cls.parsed, cls.tool_revision,
                                  cls.sem)
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

    @classmethod
    def tearDownClass(cls):
        typed_probe.TypedChunkTests.tearDownClass()

    def check(self, entry, chunk_ids, expect_returns=False):
        host_fns, host_sigs, host_types = self.host
        ext = [s for s in self.sigs if s["name"] != entry]
        allowed = self.index.fact_closure(chunk_ids, {s["name"] for s in ext})
        ext = [s for s in ext if s["name"] in allowed]
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed",
             "arguments": [
                 self.harness.sliced(self.parsed, chunk_ids),
                 {"type": "List[CheckedFunction]",
                  "value": [checked_fn_value(s) for s in ext] + host_fns},
                 {"type": "List[ResolvedSignature]",
                  "value": [resolved_sig_value(s) for s in ext] + host_sigs},
                 {"type": "List[ResolvedTypeDecl]", "value": self.facts + host_types},
                 {"type": "Bool", "value": expect_returns}],
             "semanticTarget": self.sem})
        if response.get("outcome") != "ok":
            return (response.get("error") or {}).get("code")
        return fields_map(response["result"])["status"]["value"]

    def prefix_chunk(self, entry, hi):
        groups = [("prefix", 0, hi, (), False)]
        for label, chunk, _terminal in self.index.bounded_units(
                self.table[entry], groups=groups):
            if label == "prefix":
                return chunk
        raise AssertionError("prefix group not produced")

    def test_utf8_check_has_twenty_one_statements_not_six(self):
        # The earlier "proven" two-group scheme covered statements 0..6 only.
        statements = self.index.statement_children(self.table["utf8_check"])
        self.assertEqual(len(statements), 21)

    def test_prefix_units_are_valid_up_to_six_statements(self):
        # Bindings force re-inclusion, so coverage is bounded by prefix size.
        for hi in range(1, 7):
            self.assertEqual(self.check("utf8_check", self.prefix_chunk("utf8_check", hi)),
                             "valid", f"prefix of {hi} statements")
        self.assertEqual(
            self.check("utf8_check", self.prefix_chunk("utf8_check", 7)),
            "PEP_RUNTIME_STEP_LIMIT")

    def test_groups_api_expresses_ranges_with_carried_bindings(self):
        # The proven two-group scheme must be expressible through the API.
        groups = [("g1", 0, 4, (), False), ("g2", 4, 6, (0, 2, 3), False)]
        produced = [label for label, _chunk, _terminal in
                    self.index.bounded_units(self.table["utf8_check"], groups=groups)]
        self.assertEqual(produced, ["body", "g1", "g2"])
        for label, chunk, terminal in self.index.bounded_units(
                self.table["utf8_check"], groups=groups):
            if label == "body":
                continue
            self.assertEqual(self.check("utf8_check", chunk, terminal), "valid",
                             label)


if __name__ == "__main__":
    unittest.main()
