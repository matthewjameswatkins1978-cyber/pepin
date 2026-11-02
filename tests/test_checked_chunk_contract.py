"""Hostile contract tests for the versioned checked-chunk boundary (v1).

The emitter fails closed, so the host must never hand it a chunk whose
provenance is unverified. These tests attack the host side of that boundary:
forged, missing, duplicated, narrowed, reordered, repeated and stale chunks,
plus plans that silently drop a node or duplicate a non-shared one.

Two layers, deliberately separate:
- synthetic trees exercise every refusal code without a Pep session, so the
  negative matrix stays fast and deterministic;
- one integration case drives the real staged parser, the real
  ``chunk_signatures`` and the real Pep ``analyze_chunk`` over the exact
  shared-declaration chunk shape the current chunker produces, so the
  contract is shown to describe the pipeline that exists.
"""
import copy
import pathlib
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_chunk_contract import (ChunkLedger, ContractRefusal, DocumentIndex,
                                 chunk_record, plan_chunks, plan_ids, validate_chunk)
from pep_c23 import Session, parse_target, require

ROOT = pathlib.Path(__file__).resolve().parents[1]
NL = chr(10)


def flat_node(node_id, parent_id, child_index=0, role="statement", kind="name", text=""):
    def scalar(type_name, value):
        return {"type": type_name, "value": value}
    return {"type": "FlatAstNode", "fields": [
        {"name": "id", "value": scalar("Int", str(node_id))},
        {"name": "parentId", "value": scalar("Int", str(parent_id))},
        {"name": "childIndex", "value": scalar("Int", str(child_index))},
        {"name": "role", "value": scalar("Str", role)},
        {"name": "kind", "value": scalar("Str", kind)},
        {"name": "text", "value": scalar("Str", text)},
        {"name": "integerValue", "value": scalar("Int", "0")},
        {"name": "booleanValue", "value": scalar("Bool", False)},
        {"name": "stringParts", "value": {"type": "List[Str]", "value": []}},
        {"name": "startByte", "value": scalar("Int", "0")},
        {"name": "endByte", "value": scalar("Int", "1")},
        {"name": "line", "value": scalar("Int", "1")},
        {"name": "column", "value": scalar("Int", "1")}]}


def set_node(node, **values):
    for field in node["fields"]:
        if field["name"] in values:
            field["value"]["value"] = values[field["name"]]
    return node


def report_value(document, revision, node_count, status="valid"):
    report = pep_c23.checker_report(document, revision)
    for field in report["fields"]:
        if field["name"] == "syntaxNodeCount":
            field["value"]["value"] = str(node_count)
        if field["name"] == "status":
            field["value"]["value"] = status
    return report


def field_value(node, name):
    for field in node["fields"]:
        if field["name"] == name:
            return field["value"]["value"]
    raise AssertionError(f"node has no {name}")


def two_function_tree():
    """Two tiny function subtrees: 0:{0,1,2} and 3:{3,4,5}."""
    nodes = [
        flat_node(0, -1, 0, role="", kind="function", text="first"),
        flat_node(1, 0, 0, role="statement", kind="return"),
        flat_node(2, 1, 0, role="value", kind="integer"),
        flat_node(3, -1, 1, role="", kind="function", text="second"),
        flat_node(4, 3, 0, role="statement", kind="return"),
        flat_node(5, 4, 0, role="value", kind="integer"),
    ]
    return DocumentIndex("doc-1", "rev-1", nodes)


class ChunkContractNegativeTests(unittest.TestCase):
    def setUp(self):
        self.index = two_function_tree()
        self.plan = plan_chunks(self.index, [0, 3])
        self.ledger = ChunkLedger(self.plan)

    def good_chunk(self, position=0):
        planned = self.plan.node_ids(position)
        nodes = [copy.deepcopy(node) for node in self.index.nodes_for(planned)]
        return chunk_record(self.plan, position, nodes,
                            report_value(self.plan.document, self.plan.revision, len(planned)))

    def assertRefused(self, code, callable_):
        with self.assertRaises(ContractRefusal) as caught:
            callable_()
        self.assertEqual(caught.exception.code, code, caught.exception)

    def test_plan_covers_the_document_and_a_clean_sequence_completes(self):
        described = self.plan.describe()
        self.assertEqual(described["chunkCount"], 2)
        self.assertEqual(described["nodeCount"], 6)
        self.ledger.accept(self.good_chunk(0))
        self.ledger.accept(self.good_chunk(1))
        completed = self.ledger.complete()
        self.assertEqual(completed["status"], "valid")
        self.assertEqual(completed["nodeCount"], 6)

    def test_unknown_contract_version_is_refused(self):
        chunk = self.good_chunk()
        chunk["version"] = "pep-checked-chunk-v2"
        self.assertRefused("CHUNK_VERSION_UNKNOWN", lambda: validate_chunk(self.plan, chunk))

    def test_stale_revision_is_refused(self):
        chunk = self.good_chunk()
        chunk["revision"] = "rev-0"
        self.assertRefused("CHUNK_STALE_REVISION", lambda: validate_chunk(self.plan, chunk))

    def test_forged_node_id_is_refused(self):
        chunk = self.good_chunk()
        chunk["nodes"].append(copy.deepcopy(flat_node(99, 0)))
        self.assertRefused("CHUNK_UNKNOWN_NODE", lambda: validate_chunk(self.plan, chunk))

    def test_duplicate_node_is_refused(self):
        chunk = self.good_chunk()
        chunk["nodes"].append(copy.deepcopy(chunk["nodes"][0]))
        self.assertRefused("CHUNK_DUPLICATE_NODE", lambda: validate_chunk(self.plan, chunk))

    def test_missing_planned_node_is_refused(self):
        chunk = self.good_chunk()
        chunk["nodes"] = chunk["nodes"][:-1]
        self.assertRefused("CHUNK_MISSING_NODE", lambda: validate_chunk(self.plan, chunk))

    def test_narrowed_coverage_claim_is_refused(self):
        chunk = self.good_chunk()
        chunk["coveredNodeIds"] = chunk["coveredNodeIds"][:-1]
        self.assertRefused("CHUNK_COVERAGE_MISMATCH", lambda: validate_chunk(self.plan, chunk))

    def test_report_from_another_revision_is_refused(self):
        chunk = self.good_chunk()
        chunk["report"] = report_value("doc-1", "rev-9", len(self.plan.node_ids(0)))
        self.assertRefused("CHUNK_REPORT_MISMATCH", lambda: validate_chunk(self.plan, chunk))

    def test_report_node_count_mismatch_is_refused(self):
        chunk = self.good_chunk()
        chunk["report"] = report_value(self.plan.document, self.plan.revision, 2)
        self.assertRefused("CHUNK_REPORT_COUNT_MISMATCH", lambda: validate_chunk(self.plan, chunk))

    def test_unknown_report_status_is_refused(self):
        chunk = self.good_chunk()
        chunk["report"] = report_value(self.plan.document, self.plan.revision,
                                       len(self.plan.node_ids(0)), status="probably-fine")
        self.assertRefused("CHUNK_REPORT_STATUS_UNKNOWN", lambda: validate_chunk(self.plan, chunk))

    def test_rewritten_parent_is_refused(self):
        chunk = self.good_chunk()
        child = [node for node in chunk["nodes"] if field_value(node, "id") == "2"][0]
        set_node(child, parentId="0")
        self.assertRefused("CHUNK_INVALID_PARENT_ORDER", lambda: validate_chunk(self.plan, chunk))

    def test_missing_parent_inside_the_chunk_is_refused(self):
        # A plan that splits a parent from its child is refused at plan time.
        self.assertRefused("CHUNK_PLAN_OPEN_PARENT",
                           lambda: plan_ids(self.index, [[0, 2], [1, 3, 4, 5]]))

    def test_negative_child_index_is_refused(self):
        chunk = self.good_chunk()
        set_node(chunk["nodes"][0], childIndex="-1")
        self.assertRefused("CHUNK_NEGATIVE_CHILD_INDEX", lambda: validate_chunk(self.plan, chunk))

    def test_index_outside_the_plan_is_refused(self):
        chunk = self.good_chunk()
        chunk["index"] = 7
        self.assertRefused("CHUNK_INDEX_OUT_OF_RANGE", lambda: validate_chunk(self.plan, chunk))

    def test_reordered_and_repeated_chunks_are_refused(self):
        second = self.good_chunk(1)
        self.assertRefused("CHUNK_OUT_OF_ORDER", lambda: self.ledger.accept(second))
        first = self.good_chunk(0)
        self.ledger.accept(first)
        self.assertRefused("CHUNK_REPEATED", lambda: self.ledger.accept(first))

    def test_skipped_chunk_keeps_the_sequence_incomplete(self):
        self.ledger.accept(self.good_chunk(0))
        self.assertRefused("CHUNK_INCOMPLETE", self.ledger.complete)

    def test_uncertified_external_signature_is_refused(self):
        chunk = self.good_chunk()
        chunk["suppliedSignatures"] = [3]
        self.assertRefused("CHUNK_UNSUPPLIED_SIGNATURE", lambda: validate_chunk(self.plan, chunk))
        certified = plan_chunks(self.index, [0, 3], signatures=[3])
        chunk["report"] = report_value(certified.document, certified.revision,
                                       len(certified.node_ids(0)))
        self.assertEqual(validate_chunk(certified, chunk), "valid")

    def test_plan_that_omits_a_node_is_refused(self):
        self.assertRefused("CHUNK_PLAN_INCOMPLETE", lambda: plan_chunks(self.index, [0]))

    def test_overlapping_plan_roots_are_refused(self):
        self.assertRefused("CHUNK_PLAN_OVERLAP", lambda: plan_chunks(self.index, [0, 0]))

    def test_non_contiguous_document_is_refused(self):
        nodes = [flat_node(0, -1, 0), flat_node(2, 0, 0)]
        self.assertRefused("CHUNK_COVERAGE_MISMATCH",
                           lambda: DocumentIndex("doc", "rev", nodes))

    def test_document_with_a_duplicate_node_is_refused(self):
        nodes = [flat_node(0, -1, 0), flat_node(0, -1, 1)]
        self.assertRefused("CHUNK_DUPLICATE_NODE", lambda: DocumentIndex("doc", "rev", nodes))

    def test_shared_declaration_repeats_only_where_the_plan_says_so(self):
        declaration, body = self.index.subtree(3), self.index.subtree(0)
        shared_plan = plan_ids(self.index, [list(declaration),
                                            sorted(set(body) | set(declaration))],
                               shared_roots=[3])
        for position in range(shared_plan.chunk_count):
            planned = shared_plan.node_ids(position)
            chunk = chunk_record(shared_plan, position,
                                 self.index.nodes_for(planned),
                                 report_value(shared_plan.document, shared_plan.revision,
                                              len(planned)))
            self.assertEqual(validate_chunk(shared_plan, chunk), "valid")
        repeated = ledgers = ChunkLedger(shared_plan)
        for position in range(shared_plan.chunk_count):
            ledgers.accept(chunk_record(shared_plan, position,
                                        self.index.nodes_for(shared_plan.node_ids(position)),
                                        report_value(shared_plan.document,
                                                     shared_plan.revision,
                                                     len(shared_plan.node_ids(position)))))
        self.assertEqual(ledgers.complete()["status"], "valid")
        self.assertTrue(shared_plan.is_shared(3))
        self.assertFalse(shared_plan.is_shared(0))

    def test_unshared_node_may_not_appear_in_two_chunks(self):
        # Node 0 is repeated across both chunks and is not a declared shared
        # root, so the plan itself is refused rather than the chunk.
        self.assertRefused("CHUNK_PLAN_OVERLAP",
                           lambda: plan_ids(self.index, [[0, 1, 2], [0, 3, 4, 5]]))

    def test_shared_root_must_be_a_declared_node(self):
        self.assertRefused("CHUNK_UNKNOWN_NODE",
                           lambda: plan_chunks(self.index, [0, 3], shared_roots=[42]))

    def test_shared_root_containment_guard_is_defensive(self):
        # A shared root must be whole inside some planned chunk. With full
        # coverage plus parent closure, splitting a subtree forces its
        # ancestors to repeat, and repetition is only legal inside a shared
        # root, so this guard stays unreachable through plan_chunks/plan_ids.
        # It is kept as a belt-and-braces check on a hand-built plan.
        plan = plan_ids(self.index, [list(self.index.subtree(0)), list(self.index.subtree(3))],
                        shared_roots=[3])
        for root in plan.shared_roots:
            members = set(self.index.subtree(root))
            self.assertTrue(any(members <= set(ids) for ids in plan.chunk_ids), root)


class CheckedChunkIntegrationTests(unittest.TestCase):
    """The contract must describe the pipeline that exists, not an ideal one."""

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

    @classmethod
    def tearDownClass(cls):
        cls.session.process.stdin.close()
        cls.session.process.terminate()

    def source(self):
        return ("type P { x: Int }\n"
                "fn mk(v: Int) -> P {\n  return P { x: v }\n}\n"
                "fn use(q: Int) -> Int {\n  let p = mk(q)\n  return p.x\n}\n")

    def open_parsed(self, name):
        from tests.chunk_helper import fields_map
        source = self.source()
        src = source.encode("utf-8")
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": name, "bytes": list(src)})
        require(target, "outcome", "ok", f"open {name}")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(self.session, src, target, self.tool_revision)
        return parsed, sem, fields_map(parsed)["nodes"]["value"]

    def test_shared_declaration_chunks_drive_a_complete_contract_sequence(self):
        from tests.chunk_helper import (checked_fn_value, fields_map, nval,
                                         remap_chunk, resolved_sig_value, sigs_from_tool)
        parsed, sem, nodes = self.open_parsed("contract-target")
        signatures = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_invoke", "tool": "pep-c23-checker-sigs",
                                        "arguments": [parsed], "semanticTarget": sem})
        require(signatures, "outcome", "ok", "checker signatures")
        sigs = sigs_from_tool(signatures["result"])
        self.assertEqual([sig["name"] for sig in sigs], ["mk", "use"])

        index = contract.DocumentIndex.from_parsed(parsed)
        functions = [int(nval(node, "id")) for node in nodes if nval(node, "kind") == "function"]
        declarations = [int(nval(node, "id")) for node in nodes
                        if str(nval(node, "parentId")) == "-1" and nval(node, "kind") != "function"]
        self.assertEqual(len(declarations), 1, "source has one top-level record declaration")
        declaration_ids = set(index.subtree(declarations[0]))
        chunk_ids = [sorted(declaration_ids)]
        for function in functions:
            chunk_ids.append(sorted(set(index.subtree(function)) | declaration_ids))
        plan = plan_ids(index, chunk_ids, shared_roots=declarations, signatures=functions)
        self.assertEqual(plan.chunk_count, 3)
        self.assertEqual(plan.shared_ids, frozenset(declaration_ids))

        ledger = ChunkLedger(plan)
        for position in range(plan.chunk_count):
            planned = plan.node_ids(position)
            chunk_nodes = index.nodes_for(planned)
            remapped = remap_chunk(copy.deepcopy(chunk_nodes))
            # The checker call may permute ids for transport contiguity, but the
            # permutation must be lossless and order-preserving: same count,
            # same ascending original order, no invented nodes.
            self.assertEqual(len(remapped), len(chunk_nodes))
            self.assertEqual([int(nval(node, "id")) for node in remapped],
                             list(range(len(chunk_nodes))))
            self.assertEqual([int(nval(node, "startByte")) for node in remapped],
                             sorted(int(nval(node, "startByte")) for node in chunk_nodes))
            other = [sig for sig in sigs if sig["id"] not in [str(node_id) for node_id in planned]]
            sliced = {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": remapped}
                                        if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}
            checked = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                         "arguments": [sliced,
                                                       {"type": "List[CheckedFunction]",
                                                        "value": [checked_fn_value(sig) for sig in other]},
                                                       {"type": "List[ResolvedSignature]",
                                                        "value": [resolved_sig_value(sig) for sig in other]}],
                                         "semanticTarget": sem})
            require(checked, "outcome", "ok", f"check chunk {position}")
            report = checked["result"]
            self.assertEqual(fields_map(report)["status"]["value"], "valid", report)
            ledger.accept(chunk_record(plan, position, chunk_nodes, report, functions))
        completed = ledger.complete()
        self.assertEqual(completed["status"], "valid", completed)
        self.assertEqual(completed["chunkCount"], 3)

    def test_real_report_with_a_foreign_revision_is_refused(self):
        from tests.chunk_helper import fields_map
        parsed, _, nodes = self.open_parsed("stale-target")
        index = contract.DocumentIndex.from_parsed(parsed)
        top = [int(nval_value) for nval_value in
               [fields_map(node)["id"]["value"] for node in nodes
                if str(fields_map(node)["parentId"]["value"]) == "-1"]]
        plan = plan_chunks(index, top)
        position = 0
        planned = plan.node_ids(position)
        chunk = chunk_record(plan, position, index.nodes_for(planned),
                             report_value(plan.document, "rev-from-another-session", len(planned)))
        with self.assertRaises(ContractRefusal) as caught:
            validate_chunk(plan, chunk)
        self.assertEqual(caught.exception.code, "CHUNK_REPORT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
