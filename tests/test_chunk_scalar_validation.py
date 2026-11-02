"""Scalar validation at the checked-chunk boundary (Agent 3 finding).

Agent 3 reported that ``pep_chunk_contract.py`` could be fed values that a
fail-closed consumer must never accept:

- a fractional number (3.7) accepted because the old code called ``int()``;
- a boolean accepted as an integer identifier (``bool`` is an ``int`` subclass);
- a numeric string accepted as an envelope integer;
- malformed text raising an uncaught ``ValueError`` instead of a documented
  refusal.

The repair keeps the real Pep JSONL wire format working — a typed ``Int``
field legitimately arrives as a canonical decimal string — while refusing
every lossy or ambiguous shape with a stable code. Each case below failed with
the wrong acceptance or a bare exception before the repair.

These are unit cases on purpose: they need no Pep session, so they stay fast
and deterministic while pinning the exact refusal codes.
"""
import copy
import unittest

import pep_c23
import pep_chunk_contract as contract
from pep_chunk_contract import (ChunkLedger, ContractRefusal, DocumentIndex,
                                 chunk_record, plan_chunks, validate_chunk)


def flat_node(node_id, parent_id, child_index=0, role="statement", kind="name"):
    def scalar(type_name, value):
        return {"type": type_name, "value": value}
    return {"type": "FlatAstNode", "fields": [
        {"name": "id", "value": scalar("Int", str(node_id))},
        {"name": "parentId", "value": scalar("Int", str(parent_id))},
        {"name": "childIndex", "value": scalar("Int", str(child_index))},
        {"name": "role", "value": scalar("Str", role)},
        {"name": "kind", "value": scalar("Str", kind)},
        {"name": "text", "value": scalar("Str", "")},
        {"name": "integerValue", "value": scalar("Int", "0")},
        {"name": "booleanValue", "value": scalar("Bool", False)},
        {"name": "stringParts", "value": {"type": "List[Str]", "value": []}},
        {"name": "startByte", "value": scalar("Int", "0")},
        {"name": "endByte", "value": scalar("Int", "1")},
        {"name": "line", "value": scalar("Int", "1")},
        {"name": "column", "value": scalar("Int", "1")}]}


def set_field(node, name, value):
    for field in node["fields"]:
        if field["name"] == name:
            field["value"]["value"] = value
            return node
    raise AssertionError(f"node has no field {name}")


def report_value(document, revision, node_count, status="valid"):
    report = pep_c23.checker_report(document, revision)
    for field in report["fields"]:
        if field["name"] == "syntaxNodeCount":
            field["value"]["value"] = str(node_count)
        if field["name"] == "status":
            field["value"]["value"] = status
    return report


class ScalarValidationTests(unittest.TestCase):
    def setUp(self):
        self.index = DocumentIndex("doc-1", "rev-1", [flat_node(0, -1, 0),
                                                      flat_node(1, 0, 0)])
        self.plan = plan_chunks(self.index, [0])

    def good_chunk(self):
        planned = self.plan.node_ids(0)
        return chunk_record(self.plan, 0, [copy.deepcopy(node)
                                           for node in self.index.nodes_for(planned)],
                            report_value(self.plan.document, self.plan.revision,
                                         len(planned)))

    def assertRefused(self, code, callable_):
        with self.assertRaises(ContractRefusal) as caught:
            callable_()
        self.assertEqual(caught.exception.code, code, caught.exception)

    # --- typed Pep scalars (the real wire format) -------------------------

    def test_canonical_string_integer_is_accepted(self):
        # Pep encodes Int as a decimal string; this must keep working.
        chunk = self.good_chunk()
        self.assertEqual(validate_chunk(self.plan, chunk), "valid")

    def test_fractional_node_id_is_refused(self):
        chunk = self.good_chunk()
        set_field(chunk["nodes"][1], "id", 1.5)
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_boolean_node_id_is_refused(self):
        chunk = self.good_chunk()
        set_field(chunk["nodes"][1], "id", True)
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_non_canonical_integer_text_is_refused(self):
        for text in (" 1", "1 ", "+1", "1_0", "0x10", "1.0", "", "abc", "١٢٣"):
            with self.subTest(text=text):
                chunk = self.good_chunk()
                set_field(chunk["nodes"][1], "id", text)
                self.assertRefused("CHUNK_SCALAR_FORMAT",
                                   lambda: validate_chunk(self.plan, chunk))

    def test_malformed_integer_text_is_a_contract_refusal_not_a_value_error(self):
        chunk = self.good_chunk()
        set_field(chunk["nodes"][1], "childIndex", "not-a-number")
        try:
            validate_chunk(self.plan, chunk)
        except ContractRefusal as refusal:
            self.assertEqual(refusal.code, "CHUNK_SCALAR_FORMAT")
        except ValueError as error:  # pragma: no cover - the old defect
            self.fail(f"malformed text escaped as ValueError: {error}")
        else:  # pragma: no cover - the old defect
            self.fail("malformed text was accepted")

    def test_report_node_count_accepts_canonical_and_refuses_fraction(self):
        chunk = self.good_chunk()
        for field in chunk["report"]["fields"]:
            if field["name"] == "syntaxNodeCount":
                field["value"]["value"] = 2.0
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_string_scalar_must_be_a_string(self):
        chunk = self.good_chunk()
        for field in chunk["report"]["fields"]:
            if field["name"] == "status":
                field["value"]["value"] = 7
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_wrong_record_type_is_a_type_refusal(self):
        chunk = self.good_chunk()
        chunk["report"] = {"type": "ParserProgress", "fields": []}
        self.assertRefused("CHUNK_TYPE_MISMATCH", lambda: validate_chunk(self.plan, chunk))

    # --- envelope integers (host-written, must be exact) ------------------

    def test_boolean_chunk_index_is_refused(self):
        chunk = self.good_chunk()
        chunk["index"] = True
        with self.assertRaises(ContractRefusal) as caught:
            ChunkLedger(self.plan).accept(chunk)
        self.assertEqual(caught.exception.code, "CHUNK_INDEX_OUT_OF_RANGE")

    def test_string_chunk_index_is_refused(self):
        chunk = self.good_chunk()
        chunk["index"] = "0"
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_boolean_covered_id_is_refused(self):
        chunk = self.good_chunk()
        chunk["coveredNodeIds"] = [True, 1]
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(self.plan, chunk))

    def test_boolean_supplied_signature_is_refused(self):
        plan = plan_chunks(self.index, [0], signatures=[1])
        planned = plan.node_ids(0)
        chunk = chunk_record(plan, 0, self.index.nodes_for(planned),
                             report_value(plan.document, plan.revision, len(planned)),
                             supplied_signatures=[True])
        self.assertRefused("CHUNK_SCALAR_TYPE", lambda: validate_chunk(plan, chunk))

    def test_non_integer_signature_provenance_is_refused(self):
        # Provenance ids are node ids and may arrive in the Pep wire form
        # (canonical decimal string); lossy and malformed shapes are refused
        # with distinct stable codes.
        for value, code in ((1.5, "CHUNK_SCALAR_TYPE"), (True, "CHUNK_SCALAR_TYPE"),
                            ("1_0", "CHUNK_SCALAR_FORMAT"), (" 1", "CHUNK_SCALAR_FORMAT"),
                            ("x", "CHUNK_SCALAR_FORMAT")):
            with self.subTest(value=value):
                self.assertRefused(code,
                                   lambda: plan_chunks(self.index, [0], signatures=[value]))

    def test_canonical_string_provenance_is_accepted(self):
        plan = plan_chunks(self.index, [0], signatures=["1"])
        self.assertEqual(sorted(plan.signatures), [1])

    def test_float_planned_node_id_is_refused(self):
        self.assertRefused("CHUNK_SCALAR_TYPE",
                           lambda: contract.plan_ids(self.index, [[0.0, 1]]))


if __name__ == "__main__":
    unittest.main()
