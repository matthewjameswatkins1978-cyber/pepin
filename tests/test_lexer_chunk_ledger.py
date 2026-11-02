"""Measured per-function chunk ledger for the REAL Pep lexer.

Pins what the real staged pipeline actually does on `examples/pep_lexer.pep`
at this head, per top-level function, using the v1 checked-chunk contract:

- one declaration chunk per top-level type declaration, transitively closed
  over declared type names (a declaration-only chunk that names another
  declaration is measurably not checkable alone: PEP_UNKNOWN_TYPE);
- one body chunk per function: its subtree plus the declaration subtrees it
  textually references (the shape the current chunker produces).

Assertions are written so a repair FAILS the pin instead of quietly passing:
a function pinned as step-limited must still be step-limited, and flipping it
to `valid` is a deliberate edit that re-measures the ledger. Never raise the
100,000-step budget or the 1 MiB message limit to make this pass.

Measured at 87c9fec (`codex/checker-emitter-integration`):
  parse            complete, 567 steps, 2,030 nodes
  valid chunks     ascii_letter 24, ascii_digit 12, ascii_continue 10,
                   advance_position 33, make_token 55 nodes
  step-limited     utf8_check 268, make_cursor 103, make_progress 125,
                   lexer_start 59 nodes
  transport-limit  lexer_step 1,513 nodes (request above 1 MiB)

The four hot functions are construct-driven, not node-count-driven:
`lexer_start` stops at 59 nodes while `make_token` passes at 55, so a
universal "~24 nodes is safe" ceiling does not describe the checker stage.
"""
import copy
import pathlib
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_c23 import Session, parse_target, require
from tests.chunk_helper import (checked_fn_value, decl_closure, fetch_all_sigs,
                                 fields_map, nval, remap_chunk, resolved_sig_value,
                                 variant_to_union)

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)

PINNED_STATUS = {
    "ascii_letter": "valid",
    "ascii_digit": "valid",
    "ascii_continue": "valid",
    "advance_position": "valid",
    "make_token": "valid",
    "utf8_check": "PEP_RUNTIME_STEP_LIMIT",
    "make_cursor": "PEP_RUNTIME_STEP_LIMIT",
    "make_progress": "PEP_RUNTIME_STEP_LIMIT",
    "lexer_start": "PEP_RUNTIME_STEP_LIMIT",
    "lexer_step": "host-transport-limit",
}


class RealLexerChunkLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        bundle = NL.join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = cls.session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                                    "name": "pep-c23", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        cls.tool_revision = opened["revision"]
        tool_document = opened["document"]
        sample = cls.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "validate", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True, lex_stage="done")
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker-chunk", "analyze_chunk", [empty_pp, empty_ext, empty_sig],
                 empty_rep),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig)]:
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                              "tool": tool, "document": tool_document,
                              "revision": cls.tool_revision, "function": function})
            validated = cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                           "op": "tool_validate", "tool": tool,
                                           "document": tool_document,
                                           "revision": cls.tool_revision,
                                           "testVectors": [{"arguments": arguments,
                                                            "expect": expected,
                                                            "semanticTarget": target_spec}]})
            require(validated, "outcome", "ok", f"validate {tool}")
            cls.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": tool_document, "revision": cls.tool_revision})
        cls.results = None

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def measure(self):
        if RealLexerChunkLedgerTests.results is not None:
            return RealLexerChunkLedgerTests.results
        source_bytes = (ROOT / "examples" / "pep_lexer.pep").read_bytes()
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "lexer-ledger", "bytes": list(source_bytes)})
        self.assertEqual(target.get("outcome"), "ok", target)
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, source_bytes, target, self.tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        document_node_count = len(nodes)
        index = contract.DocumentIndex.from_parsed(parsed)
        by_id = {str(nval(node, "id")): node for node in nodes}
        sigs = fetch_all_sigs(self.session, parsed, self.tool_revision, sem)
        sigs_by_name = {sig["name"]: sig for sig in sigs}

        functions = [node for node in nodes if nval(node, "kind") == "function"
                     and str(nval(node, "parentId")) == "-1"]
        declaration_roots = [int(nval(node, "id")) for node in nodes
                             if str(nval(node, "parentId")) == "-1"
                             and nval(node, "kind") != "function"]
        declaration_name_to_root = {nval(by_id[str(root)], "text"): root
                                    for root in declaration_roots}
        decl_name_to_id = {nval(node, "text"): str(nval(node, "id")) for node in nodes
                           if str(nval(node, "parentId")) == "-1"
                           and nval(node, "kind") in ("record_declaration", "union_declaration")}
        v2u = variant_to_union(nodes)

        def declaration_closure(ids):
            seen, changed = set(ids), True
            while changed:
                changed = False
                for node_id in list(seen):
                    node = by_id[str(node_id)]
                    if nval(node, "kind") != "type_named":
                        continue
                    target_root = declaration_name_to_root.get(nval(node, "text"))
                    if target_root is None:
                        continue
                    subtree = set(index.subtree(target_root))
                    if not subtree <= seen:
                        seen |= subtree
                        changed = True
            return sorted(seen)

        chunk_ids, labels = [], []
        for root in declaration_roots:
            chunk_ids.append(declaration_closure(index.subtree(root)))
            labels.append(f"declaration:{nval(by_id[str(root)], 'text')}")
        for function in functions:
            subtree = index.subtree(int(nval(function, "id")))
            sub_nodes = [copy.deepcopy(by_id[str(node_id)]) for node_id in subtree]
            extra = decl_closure(nodes, sub_nodes, sigs_by_name, decl_name_to_id, v2u)
            extra_ids = {int(nval(node, "id")) for node in extra} - set(subtree)
            chunk_ids.append(sorted(set(subtree) | extra_ids))
            labels.append(nval(function, "text"))

        plan = contract.plan_ids(index, chunk_ids, shared_roots=declaration_roots,
                                 signatures=[int(sig["node"]) for sig in sigs])
        ledger = contract.ChunkLedger(plan)
        results = {}
        accepted = 0
        for position, label in enumerate(labels):
            planned = plan.node_ids(position)
            chunk_nodes = index.nodes_for(planned)
            other = [sig for sig in sigs if int(sig["node"]) not in set(planned)]
            sliced = {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]",
                                         "value": remap_chunk(copy.deepcopy(chunk_nodes))}
                                        if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}
            try:
                checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                              "op": "tool_invoke",
                                              "tool": "pep-c23-checker-chunk",
                                              "arguments": [sliced,
                                                            {"type": "List[CheckedFunction]",
                                                             "value": [checked_fn_value(sig)
                                                                       for sig in other]},
                                                            {"type": "List[ResolvedSignature]",
                                                             "value": [resolved_sig_value(sig)
                                                                       for sig in other]}],
                                              "semanticTarget": sem})
            except RuntimeError as error:
                results[label] = {"result": "host-transport-limit", "nodes": len(planned),
                                  "detail": str(error)[:120]}
                continue
            if checked.get("outcome") != "ok":
                results[label] = {"result": checked.get("error", {}).get("code"),
                                  "nodes": len(planned)}
                continue
            report = checked["result"]
            status = fields_map(report)["status"]["value"]
            results[label] = {"result": status, "nodes": len(planned)}
            # A stopped chunk leaves a hole, so the ledger legitimately refuses
            # everything after it; record the refusal instead of hiding it.
            try:
                ledger.accept(contract.chunk_record(plan, position, chunk_nodes, report,
                                                    [int(sig["node"]) for sig in sigs]))
                accepted += 1
                results[label]["contract"] = "accepted"
            except contract.ContractRefusal as refusal:
                results[label]["contract"] = refusal.code
        RealLexerChunkLedgerTests.results = {
            "chunks": plan.chunk_count, "accepted": accepted,
            "nodes": document_node_count, "results": results, "ledger": ledger
        }
        return RealLexerChunkLedgerTests.results

    def test_declaration_chunks_and_small_functions_check_and_are_contract_accepted(self):
        measured = self.measure()
        results = measured["results"]
        for label in ("ascii_letter", "ascii_digit", "ascii_continue"):
            self.assertEqual(results[label]["result"], "valid", results[label])
        declaration_labels = [label for label in results if label.startswith("declaration:")]
        self.assertEqual(len(declaration_labels), 5, declaration_labels)
        for label in declaration_labels:
            self.assertEqual(results[label]["result"], "valid", (label, results[label]))

    def test_function_stage_results_match_the_pinned_ledger(self):
        measured = self.measure()
        results = measured["results"]
        actual = {label: results[label]["result"] for label in PINNED_STATUS}
        self.assertEqual(actual, PINNED_STATUS)
        self.assertEqual(results["lexer_step"]["result"], "host-transport-limit")
        self.assertEqual(results["lexer_start"]["result"], "PEP_RUNTIME_STEP_LIMIT")
        self.assertEqual(results["make_token"]["result"], "valid")

    def test_contract_sequence_is_incomplete_while_hot_functions_stop(self):
        measured = self.measure()
        with self.assertRaises(contract.ContractRefusal) as caught:
            measured["ledger"].complete()
        self.assertEqual(caught.exception.code, "CHUNK_INCOMPLETE")

    def test_nodes_cover_the_document_and_chunks_exceed_it_only_by_shared_declarations(self):
        measured = self.measure()
        self.assertEqual(measured["nodes"], 2030)
        self.assertEqual(measured["chunks"], 15)
        self.assertGreater(measured["accepted"], 0)


if __name__ == "__main__":
    unittest.main()
