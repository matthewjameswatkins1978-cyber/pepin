"""Agent 3 hostile probe: scalar type enforcement at the checked-chunk boundary.

Claim under attack (A1-owned `pep_chunk_contract.py`, pinned commit below):

    "The checked-chunk validator fails closed on malformed transport scalars:
     a non-integer in an Int position, or a negative child index, is refused
     with a stable ContractRefusal code."

Each case below submits one malformed chunk to `validate_chunk` /
`DocumentIndex` and records whether the contract refused it (ContractRefusal)
or let it through / died on a non-contract exception.

Exit code: 0 = every claim case refused (claim not falsified here),
           1 = at least one claim case was NOT refused (claim falsified).

Usage: python hostile_chunk_scalar_types.py [path-to-repo-root]
The repo root must contain pep_chunk_contract.py at the pinned revision.
"""
import copy
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import (ChunkLedger, ContractRefusal, DocumentIndex,  # noqa: E402
                                 chunk_record, plan_chunks, validate_chunk)

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


def set_field(node, name, value):
    for field in node["fields"]:
        if field["name"] == name:
            field["value"]["value"] = value
            return node
    raise AssertionError(name)


def report_value(document, revision, node_count, status="valid"):
    report = contract_report(document, revision)
    for field in report["fields"]:
        if field["name"] == "syntaxNodeCount":
            field["value"]["value"] = str(node_count)
        if field["name"] == "status":
            field["value"]["value"] = status
    return report


def contract_report(document, revision):
    # Same shape pep_c23.checker_report builds, without importing pep_c23.
    return {"type": "CheckerReport", "fields": [
        {"name": "document", "value": scalar("Str", document)},
        {"name": "revision", "value": scalar("Str", revision)},
        {"name": "status", "value": scalar("Str", "valid")},
        {"name": "syntaxNodeCount", "value": scalar("Int", 0)},
        {"name": "functions", "value": {"type": "List[CheckedFunction]", "value": []}},
        {"name": "bindings", "value": {"type": "List[BindingFact]", "value": []}},
        {"name": "references", "value": {"type": "List[ResolvedName]", "value": []}},
        {"name": "calls", "value": {"type": "List[ResolvedCall]", "value": []}},
        {"name": "expressionTypes", "value": {"type": "List[ExpressionTypeFact]", "value": []}},
        {"name": "holes", "value": {"type": "List[HoleFact]", "value": []}}]}


def tree(start=0):
    """Two function subtrees: n:{n,n+1,n+2} and n+3:{n+3,n+4,n+5}."""
    base = start
    return DocumentIndex("doc-1", "rev-1", [
        flat_node(base + 0, -1, 0, role="", kind="function", text="first"),
        flat_node(base + 1, base + 0, 0, kind="return"),
        flat_node(base + 2, base + 1, 0, role="value", kind="integer"),
        flat_node(base + 3, -1, 1, role="", kind="function", text="second"),
        flat_node(base + 4, base + 3, 0, kind="return"),
        flat_node(base + 5, base + 4, 0, role="value", kind="integer"),
    ])


def good_chunk(plan, position=0):
    planned = plan.node_ids(position)
    nodes = [copy.deepcopy(node) for node in plan.index.nodes_for(planned)]
    return chunk_record(plan, position, nodes,
                        report_value(plan.document, plan.revision, len(planned)))


def probe(name, claim, mutate, expect_refusal=True):
    """Run one hostile case. Records outcome; `claim` cases gate the exit code."""
    index = tree()
    # Node 0 is certified as an external signature so the suppliedSignatures
    # cases are decided on typing, not on an empty provenance set.
    plan = plan_chunks(index, [0, 3], signatures=(0,))
    chunk = mutate(good_chunk(plan, 0))
    record = {"case": name, "claim_case": claim,
              "expect": "ContractRefusal" if expect_refusal else "ACCEPTED"}
    try:
        status = validate_chunk(plan, chunk)
        record["outcome"] = "ACCEPTED"
        record["detail"] = f"validator returned status={status!r} for a malformed chunk"
    except ContractRefusal as refusal:
        record["outcome"] = "REFUSED"
        record["code"] = refusal.code
        record["detail"] = str(refusal)
    except Exception as error:  # noqa: BLE001 - the point is that it is not a refusal
        record["outcome"] = "NON_CONTRACT_EXCEPTION"
        record["code"] = type(error).__name__
        record["detail"] = str(error)
    record["falsified"] = bool(
        claim and ((expect_refusal and record["outcome"] != "REFUSED") or
                   (not expect_refusal and record["outcome"] != "ACCEPTED")))
    RESULTS.append(record)
    return record


def mutate_child_index_float(node_field_value=-0.5):
    def mutate(chunk):
        for node in chunk["nodes"]:
            if node["fields"][0]["value"]["value"] == "0":
                set_field(node, "childIndex", node_field_value)
        return chunk
    return mutate


def mutate_parent_float(chunk):
    for node in chunk["nodes"]:
        if node["fields"][0]["value"]["value"] == "2":
            set_field(node, "parentId", 1.9)  # planned parent is 1
    return chunk


def mutate_id_float(chunk):
    for node in chunk["nodes"]:
        if node["fields"][0]["value"]["value"] == "2":
            set_field(node, "id", 2.9)  # planned id is 2
    return chunk


def mutate_covered_bools(chunk):
    chunk["coveredNodeIds"] = [False, True, 2]  # planned: [0, 1, 2]
    return chunk


def mutate_covered_strings(chunk):
    chunk["coveredNodeIds"] = ["0", "1", "2"]
    return chunk


def mutate_node_id_text(chunk):
    for node in chunk["nodes"]:
        if node["fields"][0]["value"]["value"] == "2":
            set_field(node, "id", "two")
    return chunk


def mutate_report_count_float(chunk):
    for field in chunk["report"]["fields"]:
        if field["name"] == "syntaxNodeCount":
            field["value"]["value"] = 3.0
    return chunk


def mutate_bool_index(chunk):
    chunk["index"] = False  # planned position 0
    return chunk


def mutate_string_signature(chunk):
    chunk["suppliedSignatures"] = ["0"]  # plan certified 0 as an int
    return chunk


def mutate_signed_signature(chunk):
    chunk["suppliedSignatures"] = [0]
    return chunk


def observation_non_zero_based_ids():
    """Do node ids have to start at 0? (Earlier #16 review raised this case.)"""
    record = {"case": "document ids not starting at 0", "claim_case": False}
    try:
        index = tree(start=5)  # ids 5..10, contiguous, parents precede children
        plan = plan_chunks(index, [5, 8])
        record["outcome"] = "ACCEPTED"
        record["detail"] = (f"ids {list(index.node_ids())} planned into "
                            f"{plan.chunk_count} chunks; no refusal")
    except ContractRefusal as refusal:
        record["outcome"] = "REFUSED"
        record["code"] = refusal.code
        record["detail"] = str(refusal)
    except Exception as error:  # noqa: BLE001
        record["outcome"] = "NON_CONTRACT_EXCEPTION"
        record["code"] = type(error).__name__
        record["detail"] = str(error)
    RESULTS.append(record)


def main():
    probe("negative childIndex as float -0.5", True, mutate_child_index_float(-0.5))
    probe("negative childIndex as int -1 (control)", True,
          mutate_child_index_float(-1))
    probe("node id as text 'two'", True, mutate_node_id_text)
    probe("coveredNodeIds as bools", True, mutate_covered_bools)
    probe("coveredNodeIds as strings", True, mutate_covered_strings)
    probe("parentId as float 1.9 (planned 1)", True, mutate_parent_float)
    probe("node id as float 2.9 (planned 2)", True, mutate_id_float)
    probe("report syntaxNodeCount as float 3.0", True, mutate_report_count_float)
    probe("chunk index as bool False", True, mutate_bool_index)
    probe("suppliedSignatures as string", True, mutate_string_signature)
    probe("suppliedSignatures as int (control)", True, mutate_signed_signature,
          expect_refusal=False)
    observation_non_zero_based_ids()

    falsified = [item for item in RESULTS if item.get("falsified")]
    print(f"REPO={REPO}")
    print(f"CONTRACT_VERSION={contract.CONTRACT_VERSION}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item.get('code')})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
