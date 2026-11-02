"""Agent 3 hostile probe: forged facts, id-space and plan-edge attacks on
`pep-checked-chunk-v1` (A1-owned), anchored to the documented refusal codes.

Reference: `docs/CHECKED_CHUNK_CONTRACT.md` at the pinned revision (refusal
code list + plan invariants + scalar rules). This probe is deliberately
additive to A1's own `tests/test_checked_chunk_contract.py` (27 named cases):
it attacks the documented edges that suite does not name — wrong record type
tags, cross-document report/chunk identity, ascending/unique enforcement on
`coveredNodeIds`, bool `suppliedSignatures`, case-sensitive report status,
plan-time empty/open-parent shapes.

Each claim case states a documented behaviour. `expect` is the exact code
where the document pins it, otherwise "any refusal". A claim is falsified by
an ACCEPTED outcome or a non-ContractRefusal exception. Observations
(claim_case=false) are recorded without gating the exit code.

Exit code: 0 = no claim falsified, 1 = at least one claim falsified.

Usage: python hostile_chunk_forged_facts.py [repo-root-with-pep_chunk_contract]
"""
import copy
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import (ChunkLedger, ContractRefusal, DocumentIndex,  # noqa: E402
                                 chunk_record, plan_chunks, plan_ids, validate_chunk)

RESULTS = []


def scalar(type_name, value):
    return {"type": type_name, "value": value}


def flat_node(node_id, parent_id, child_index=0, role="statement", kind="name", text=""):
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


def contract_report(document, revision, status="valid", node_count=0):
    return {"type": "CheckerReport", "fields": [
        {"name": "document", "value": scalar("Str", document)},
        {"name": "revision", "value": scalar("Str", revision)},
        {"name": "status", "value": scalar("Str", status)},
        {"name": "syntaxNodeCount", "value": scalar("Int", str(node_count))},
        {"name": "functions", "value": {"type": "List[CheckedFunction]", "value": []}},
        {"name": "bindings", "value": {"type": "List[BindingFact]", "value": []}},
        {"name": "references", "value": {"type": "List[ResolvedName]", "value": []}},
        {"name": "calls", "value": {"type": "List[ResolvedCall]", "value": []}},
        {"name": "expressionTypes", "value": {"type": "List[ExpressionTypeFact]", "value": []}},
        {"name": "holes", "value": {"type": "List[HoleFact]", "value": []}}]}


def tree(document="doc-1", revision="rev-1"):
    """Two function subtrees: 0:{0,1,2} and 3:{3,4,5} (roots have parent -1)."""
    return DocumentIndex(document, revision, [
        flat_node(0, -1, 0, role="", kind="function", text="first"),
        flat_node(1, 0, 0, kind="return"),
        flat_node(2, 1, 0, role="value", kind="integer"),
        flat_node(3, -1, 1, role="", kind="function", text="second"),
        flat_node(4, 3, 0, kind="return"),
        flat_node(5, 4, 0, role="value", kind="integer"),
    ])


def good_plan():
    return plan_chunks(tree(), [0, 3], signatures=(0,))


def good_chunk(plan, position=0):
    planned = plan.node_ids(position)
    nodes = [copy.deepcopy(node) for node in plan.index.nodes_for(planned)]
    report = contract_report(plan.document, plan.revision, node_count=len(planned))
    return chunk_record(plan, position, nodes, report)


def set_field(node, name, value):
    for field in node["fields"]:
        if field["name"] == name:
            field["value"]["value"] = value
            return node
    raise AssertionError(name)


def set_report_field(report, name, value):
    for field in report["fields"]:
        if field["name"] == name:
            field["value"]["value"] = value
            return report
    raise AssertionError(name)


def record(case, claim, expect, outcome, detail=""):
    if claim:
        if expect == "any refusal":
            falsified = outcome != "REFUSED"
        else:
            falsified = outcome != "REFUSED" or detail != expect
    else:
        falsified = False
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def run_refusal(record_case, claim, expect, thunk):
    """Execute a thunk that should raise ContractRefusal; record the outcome."""
    try:
        result = thunk()
    except ContractRefusal as refusal:
        record(record_case, claim, expect, "REFUSED", refusal.code)
    except Exception as error:  # noqa: BLE001 - not a refusal is the point
        record(record_case, claim, expect, "NON_CONTRACT_EXCEPTION",
               f"{type(error).__name__}: {error}")
    else:
        record(record_case, claim, expect, "ACCEPTED", repr(result)[:120])


def main():
    plan = good_plan()

    # ---- plan-time edges -------------------------------------------------
    run_refusal("P1 empty plan refused (CHUNK_PLAN_EMPTY)", True, "CHUNK_PLAN_EMPTY",
                lambda: plan_chunks(tree(), []))

    def open_parent_plan():
        # chunk A holds {1,2} but node 1's parent 0 sits in chunk B -> not parent-closed
        return plan_ids(tree(), [[1, 2], [0, 3, 4, 5]])
    run_refusal("P2 plan chunk that opens a parent refused (CHUNK_PLAN_OPEN_PARENT)",
                True, "CHUNK_PLAN_OPEN_PARENT", open_parent_plan)

    # ---- record/type edges ----------------------------------------------
    def wrong_node_tag():
        chunk = good_chunk(plan)
        chunk["nodes"][0]["type"] = "AstNode"
        return validate_chunk(plan, chunk)
    run_refusal("P3 node with wrong record type tag refused (CHUNK_TYPE_MISMATCH)",
                True, "CHUNK_TYPE_MISMATCH", wrong_node_tag)

    def wrong_nodes_shape():
        chunk = good_chunk(plan)
        chunk["nodes"] = [1, 2, 3]  # bare ints instead of FlatAstNode records
        return validate_chunk(plan, chunk)
    run_refusal("P4 nodes as bare int list refused", True, "any refusal",
                wrong_nodes_shape)

    # ---- cross-document identity ----------------------------------------
    def cross_document_report():
        chunk = good_chunk(plan)
        set_report_field(chunk["report"], "document", "other-doc-9")
        return validate_chunk(plan, chunk)
    run_refusal("P5 report from another DOCUMENT refused (CHUNK_REPORT_MISMATCH)",
                True, "CHUNK_REPORT_MISMATCH", cross_document_report)

    def cross_document_chunk():
        chunk = good_chunk(plan)
        chunk["document"] = "other-doc-9"
        return validate_chunk(plan, chunk)
    run_refusal("P6 chunk envelope from another DOCUMENT refused", True, "any refusal",
                cross_document_chunk)

    # ---- report status edges --------------------------------------------
    def status_bool():
        chunk = good_chunk(plan)
        set_report_field(chunk["report"], "status", True)  # bool inside Str field
        return validate_chunk(plan, chunk)
    run_refusal("P7 report.status as bool refused (scalar rule)", True, "any refusal",
                status_bool)

    def status_wrong_case():
        chunk = good_chunk(plan)
        set_report_field(chunk["report"], "status", "VALID")
        return validate_chunk(plan, chunk)
    run_refusal("P8 report.status 'VALID' refused (CHUNK_REPORT_STATUS_UNKNOWN)",
                True, "CHUNK_REPORT_STATUS_UNKNOWN", status_wrong_case)

    # ---- coveredNodeIds: documented 'ascending unique' -------------------
    def covered_reversed():
        chunk = good_chunk(plan)
        chunk["coveredNodeIds"] = list(reversed(chunk["coveredNodeIds"]))
        return validate_chunk(plan, chunk)
    run_refusal("P9 coveredNodeIds descending refused (documented ascending)",
                True, "any refusal", covered_reversed)

    def covered_duplicate():
        chunk = good_chunk(plan)
        ids = chunk["coveredNodeIds"]
        chunk["coveredNodeIds"] = ids + [ids[0]]
        return validate_chunk(plan, chunk)
    run_refusal("P10 coveredNodeIds with duplicate entry refused (documented unique)",
                True, "any refusal", covered_duplicate)

    # ---- host envelope integers: bool signatures -------------------------
    def signatures_false():
        plan2 = plan_chunks(tree(), [0, 3], signatures=(0,))
        chunk = good_chunk(plan2)
        chunk["suppliedSignatures"] = [False]  # False == 0 in Python
        return validate_chunk(plan2, chunk)
    run_refusal("P11 suppliedSignatures [False] refused (bool is not an int here)",
                True, "any refusal", signatures_false)

    def signatures_true():
        plan2 = plan_chunks(tree(), [0, 3], signatures=(0,))
        chunk = good_chunk(plan2)
        chunk["suppliedSignatures"] = [True]
        return validate_chunk(plan2, chunk)
    run_refusal("P12 suppliedSignatures [True] refused", True, "any refusal",
                signatures_true)

    # ---- observations (no claim) ----------------------------------------
    try:
        ledger = ChunkLedger(plan)
        record("O1 ChunkLedger.complete() is False before any chunk accepted",
               False, "observed", repr(ledger.complete()))
    except Exception as error:  # noqa: BLE001
        record("O1 ChunkLedger constructs empty (complete() before any chunk)",
               False, "observed", f"{type(error).__name__}: {error}")

    try:
        version = contract.CONTRACT_VERSION
        record("O2 CONTRACT_VERSION", False, "observed", version)
    except Exception as error:  # noqa: BLE001
        record("O2 CONTRACT_VERSION", False, "observed", f"{type(error).__name__}")

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(f"CONTRACT_VERSION={getattr(contract, 'CONTRACT_VERSION', '?')}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
