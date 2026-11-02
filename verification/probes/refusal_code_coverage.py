"""Agent 3 cited-vs-asserted refusal-code sweep at A1 `05add76` (head).

Audit: every `CHUNK_*` code cited in `docs/CHECKED_CHUNK_CONTRACT.md` must be
asserted by some test (builder `tests/**` or Agent 3 `verification/**`). At
this head: 25 cited, 22 builder-asserted, 16 verification-asserted, **2 gaps**:

  G1 `CHUNK_OPEN_PARENT` — implemented at `validate_chunk` but asserted nowhere.
      Claim: reachable — a chunk that passes coverage with an exact planned id
      list still gets refused when a node's `parentId` names a missing node
      (mutated after construction; transport-canonical string Int).
  G2 `CHUNK_PLAN_SHARED_NOT_PLANNED` — implemented at `_plan` but asserted
      nowhere. Builder comment claims the guard is unreachable through
      plan_chunks/plan_ids (for full-coverage plans). Claim: it IS reachable
      through plan_ids with an INCOMPLETE-coverage plan that names a shared
      root lying in no planned chunk — the shared check runs before the
      coverage-incomplete check.

Both claims closing = the sweep ends 25/25 cited-and-asserted. Any refusal
other than the documented code (or acceptance) falsifies.

Pure Python contract layer: no session, no emission, no native build.
Exit: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python refusal_code_coverage.py <repo-root-with-pep_chunk_contract>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import (ContractRefusal, DocumentIndex,  # noqa: E402
                                 chunk_record, plan_ids)

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


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def tree():
    return DocumentIndex("doc-1", "rev-1", [
        flat_node(0, -1, 0, role="", kind="function", text="first"),
        flat_node(1, 0, 0, kind="return"),
        flat_node(2, 1, 0, role="value", kind="integer"),
        flat_node(3, -1, 1, role="", kind="function", text="second"),
        flat_node(4, 3, 0, kind="return"),
        flat_node(5, 4, 0, role="value", kind="integer"),
    ])


def run_refusal(case, expect_code, thunk):
    try:
        result = thunk()
    except ContractRefusal as refusal:
        outcome = refusal.code if refusal.code == expect_code else f"other:{refusal.code}"
        record(case, True, expect_code, outcome, refusal.code)
    except Exception as error:  # noqa: BLE001
        record(case, True, expect_code, "NON_CONTRACT_EXCEPTION",
               f"{type(error).__name__}: {error}")
    else:
        record(case, True, expect_code, "ACCEPTED", repr(result)[:100])


def main():
    index = tree()

    # ---- G1: chunk-time CHUNK_OPEN_PARENT (validate_chunk:404) -------------
    def g1():
        plan = plan_ids(index, [list(index.subtree(0)), list(index.subtree(3))])
        nodes = index.nodes_for(plan.node_ids(0))
        report = contract_chunk_report(plan, 0, len(plan.node_ids(0)))
        chunk = chunk_record(plan, 0, nodes, report)
        # Same id list (coverage passes), parent mutated to a missing node.
        for node in chunk["nodes"]:
            fields = {f["name"]: f["value"] for f in node["fields"]}
            if str(fields["id"]["value"]) == "1":
                for field in node["fields"]:
                    if field["name"] == "parentId":
                        field["value"]["value"] = "-5"
        return contract.validate_chunk(plan, chunk)

    run_refusal("G1 cited CHUNK_OPEN_PARENT is reachable and fires exactly",
                "CHUNK_OPEN_PARENT", g1)

    # ---- G2: plan-time CHUNK_PLAN_SHARED_NOT_PLANNED (_plan:319) -----------
    def g2():
        # Incomplete coverage: chunk 2 planned nowhere; shared root 3 named.
        # Per-node checks pass; the shared-root check runs before coverage.
        return plan_ids(index, [[0, 1, 2]], shared_roots=(3,))

    run_refusal("G2 cited CHUNK_PLAN_SHARED_NOT_PLANNED is reachable and fires "
                "exactly (incomplete plan naming an unplanned shared root)",
                "CHUNK_PLAN_SHARED_NOT_PLANNED", g2)

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print("AUDIT doc_codes=25 builder_asserted=22 verification_asserted=16 "
          "gaps_before_probe=2 (CHUNK_OPEN_PARENT, CHUNK_PLAN_SHARED_NOT_PLANNED)")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


def contract_chunk_report(plan, position, node_count):
    return {"type": "CheckerReport", "fields": [
        {"name": "document", "value": scalar("Str", plan.document)},
        {"name": "revision", "value": scalar("Str", plan.revision)},
        {"name": "status", "value": scalar("Str", "valid")},
        {"name": "syntaxNodeCount", "value": scalar("Int", str(node_count))},
        {"name": "functions", "value": {"type": "List[CheckedFunction]", "value": []}},
        {"name": "bindings", "value": {"type": "List[BindingFact]", "value": []}},
        {"name": "references", "value": {"type": "List[ResolvedName]", "value": []}},
        {"name": "calls", "value": {"type": "List[ResolvedCall]", "value": []}},
        {"name": "expressionTypes", "value": {"type": "List[ExpressionTypeFact]", "value": []}},
        {"name": "holes", "value": {"type": "List[HoleFact]", "value": []}},
        {"name": "diagnostics", "value": {"type": "List[Diagnostic]", "value": []}}]}


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # harness failure must NOT read as falsification
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
