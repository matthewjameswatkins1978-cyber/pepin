"""Cross-chunk call facts: the contract a native emitter depends on.

When a callee is supplied as an external declaration, it carries no
identifying id: every external function reports semanticId 9000 and
syntaxId 1000000000, and `ResolvedCall.calleeId` is therefore 9000 too.
The only reliable cross-chunk link is the call node's own text, reached via
`ResolvedCall.syntaxId`. This test pins that, so a later checker change
cannot silently break cross-chunk lowering for the emitter.
"""
import unittest

import pep_chunk_contract as contract
from pep_c23 import Session, require, parse_target
from tests import test_chunk_typed as typed_probe
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, remap_chunk, resolved_sig_value)

SOURCE = (b"fn callee(x: Int) -> Int {\n  return x\n}\n"
          b"fn caller(y: Int) -> Int {\n  return callee(y)\n}\n")


class CrossChunkCallFactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = typed_probe.TypedChunkTests("test_make_token_body_only_stays_valid_with_facts")
        typed_probe.TypedChunkTests.setUpClass()
        cls.session = typed_probe.TypedChunkTests.session
        cls.tool_revision = typed_probe.TypedChunkTests.tool_revision

        target = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "xcall", "bytes": list(SOURCE)})
        require(target, "outcome", "ok", "open cross-call fixture")
        cls.sem = {"document": target["document"],
                   "revision": target["revision"], "entryFunctions": []}
        cls.parsed = parse_target(cls.session, SOURCE, target, cls.tool_revision)
        cls.nodes = fields_map(cls.parsed)["nodes"]["value"]
        cls.index = contract.DocumentIndex.from_parsed(cls.parsed)
        cls.sigs = fetch_all_sigs(cls.session, cls.parsed, cls.tool_revision,
                                  cls.sem)
        table = {str(nval(n, "text")): int(nval(n, "id")) for n in cls.nodes
                 if nval(n, "kind") == "function"
                 and str(nval(n, "parentId")) == "-1"}
        # Chunk the caller only; the callee becomes an external declaration.
        cls.keep = cls.index.subtree(table["caller"])
        cls.ext = [s for s in cls.sigs if s["name"] != "caller"]
        args = [cls.harness.sliced(cls.parsed, cls.keep),
                {"type": "List[CheckedFunction]",
                 "value": [checked_fn_value(s) for s in cls.ext]},
                {"type": "List[ResolvedSignature]",
                 "value": [resolved_sig_value(s) for s in cls.ext]},
                {"type": "List[ResolvedTypeDecl]", "value": []},
                {"type": "Bool", "value": True}]
        response = cls.session.send(
            {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
             "tool": "pep-c23-checker-chunk-typed", "arguments": args,
             "semanticTarget": cls.sem})
        require(response, "outcome", "ok", "check caller chunk")
        cls.report = fields_map(response["result"])

    @classmethod
    def tearDownClass(cls):
        typed_probe.TypedChunkTests.tearDownClass()

    def test_caller_chunk_checks_valid_with_external_callee(self):
        self.assertEqual(self.report["status"]["value"], "valid")
        self.assertEqual(self.report["diagnostics"]["value"], [])

    def test_external_declarations_carry_placeholder_ids(self):
        # Every external function shares these ids, so ids cannot identify a
        # cross-chunk target.
        external = [fields_map(f) for f in self.report["functions"]["value"]
                    if fields_map(f)["name"]["value"] == "callee"]
        self.assertEqual(len(external), 1)
        self.assertEqual(external[0]["semanticId"]["value"], "9000")
        self.assertEqual(external[0]["syntaxId"]["value"], "1000000000")
        for s in self.ext:
            self.assertEqual(s["semid"], 9000, s)

    def test_resolved_call_points_at_the_call_node_which_names_the_callee(self):
        calls = self.report["calls"]["value"]
        self.assertEqual(len(calls), 1)
        call = fields_map(calls[0])
        # calleeId is the shared placeholder, not an identifier.
        self.assertEqual(call["calleeId"]["value"], "9000")
        # The chunk's own function keeps a real id.
        self.assertEqual(call["callerId"]["value"], "100000")
        # syntaxId indexes the chunk, and that node names the callee.
        syntax_id = int(call["syntaxId"]["value"])
        by_chunk_id = {}
        for position, old_id in enumerate(sorted(self.keep)):
            by_chunk_id[position] = old_id
        original = by_chunk_id[syntax_id]
        match = [n for n in self.nodes if int(nval(n, "id")) == original]
        self.assertEqual(len(match), 1)
        self.assertEqual(nval(match[0], "kind"), "call")
        self.assertEqual(nval(match[0], "text"), "callee")

    def test_checked_function_has_no_parameter_facts(self):
        # Parameters are only available through ResolvedSignature, so a
        # cross-chunk caller must be lowered signature-first.
        fields = [f["name"] for f in self.report["functions"]["value"][0]["fields"]]
        self.assertNotIn("params", fields)
        self.assertIn("arity", fields)
        callee_sig = [s for s in self.ext if s["name"] == "callee"][0]
        self.assertEqual([p[0] for p in callee_sig["ptypes"]], ["Int"])


if __name__ == "__main__":
    unittest.main()

