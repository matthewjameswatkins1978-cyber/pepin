"""The staged route as a product capability, not test-only machinery.

`DocumentIndex.bounded_units` yields checking units for one function smallest
first, and its full output is a gapless cover of that function's statements.
These tests drive the real checker through it, so the route Lucy depends on is
exercised through the contract module rather than through test helpers.
"""
import copy
import unittest

import pep_chunk_contract as contract
from pep_c23 import parse_target
from tests import test_chunk_typed as typed_probe
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, remap_chunk, resolved_sig_value)


class BoundedUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = typed_probe.TypedChunkTests(
            "test_make_token_body_only_stays_valid_with_facts")
        typed_probe.TypedChunkTests.setUpClass()
        cls.session = typed_probe.TypedChunkTests.session
        cls.tool_revision = typed_probe.TypedChunkTests.tool_revision
        cls.source = (typed_probe.ROOT / "stdlib" / "collections.pep").read_bytes()
        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "units", "bytes": list(cls.source)})
        assert target.get("outcome") == "ok", target
        cls.target = target
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
        cls.table = {str(nval(n, "text")): int(nval(n, "id")) for n in cls.nodes
                     if nval(n, "kind") == "function"
                     and str(nval(n, "parentId")) == "-1"}

    @classmethod
    def tearDownClass(cls):
        typed_probe.TypedChunkTests.tearDownClass()

    def check(self, entry, chunk_ids, expect_returns):
        ext = [s for s in self.sigs if s["name"] != entry]
        allowed = self.index.fact_closure(chunk_ids, {s["name"] for s in ext})
        ext = [s for s in ext if s["name"] in allowed]
        response = self.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed",
             "arguments": [
                 self.harness.sliced(self.parsed, chunk_ids),
                 {"type": "List[CheckedFunction]",
                  "value": [checked_fn_value(s) for s in ext]},
                 {"type": "List[ResolvedSignature]",
                  "value": [resolved_sig_value(s) for s in ext]},
                 {"type": "List[ResolvedTypeDecl]", "value": self.facts},
                 {"type": "Bool", "value": expect_returns}],
             "semanticTarget": self.sem})
        if response.get("outcome") != "ok":
            return (response.get("error") or {}).get("code"), []
        report = fields_map(response["result"])
        return report["status"]["value"], report["diagnostics"]["value"]

    def units(self, entry):
        return list(self.index.bounded_units(self.table[entry]))

    def test_whole_body_is_the_first_unit_and_fits_for_most_functions(self):
        # 105 of the module's 107 functions check valid as a single body unit.
        for entry in ("list_int_min_between", "list_int_count_runs",
                      "list_bool_has_true_majority"):
            label, chunk, terminal = self.units(entry)[0]
            self.assertEqual(label, "body")
            self.assertTrue(terminal)
            status, diagnostics = self.check(entry, chunk, terminal)
            self.assertEqual(status, "valid", (entry, diagnostics))

    def test_residual_functions_are_covered_by_smaller_units(self):
        # These two need units below statement granularity, and the route
        # reaches them through the contract module alone.
        for entry in ("list_int_min_index_between", "list_int_max_index_between"):
            accepted = None
            for label, chunk, terminal in self.units(entry):
                status, diagnostics = self.check(entry, chunk, terminal)
                if status == "valid" and not diagnostics:
                    accepted = label
                    break
            self.assertIsNotNone(accepted, f"no unit of {entry} checked valid")

    def test_body_units_keep_original_byte_spans(self):
        # A unit must not rewrite source identity: the call node inside the
        # chosen unit still carries real offsets.
        _label, chunk, _terminal = self.units("list_int_min_between")[0]
        nodes = [n for n in self.nodes if int(nval(n, "id")) in set(chunk)]
        called = [n for n in nodes if nval(n, "kind") == "call"]
        for node in nodes:
            for key in ("startByte", "endByte"):
                self.assertGreaterEqual(int(nval(node, key)), 0)
        self.assertTrue(all(int(nval(n, "endByte")) > int(nval(n, "startByte"))
                            for n in called))

    def test_statement_units_are_non_terminal_by_default(self):
        # Statement units must not be checked as terminal: doing so draws a
        # spurious missing-return diagnostic for every one of them.
        _label, chunk, terminal = self.units("list_int_min_between")[1]
        self.assertFalse(terminal)
        status, diagnostics = self.check("list_int_min_between", chunk, terminal)
        self.assertEqual(status, "valid", diagnostics)

    def test_every_function_is_fully_covered_by_valid_units(self):
        # Strong claim: the union of valid units covers every statement node
        # of the function, not merely "some unit checks valid". Driven only
        # through the contract API.
        partial = []
        for entry in self.table:
            function_id = self.table[entry]
            statements = self.index.statement_children(function_id)
            statement_nodes = {node_id for root in statements
                               for node_id in self.index.subtree(root)}
            covered = set()
            for _label, chunk, terminal in self.units(entry):
                status, diagnostics = self.check(entry, chunk, terminal)
                if status == "valid" and not diagnostics:
                    covered.update(chunk)
            missing = statement_nodes - covered
            if missing:
                partial.append((entry, len(missing)))
        self.assertEqual(partial, [], partial)
if __name__ == "__main__":
    unittest.main()
