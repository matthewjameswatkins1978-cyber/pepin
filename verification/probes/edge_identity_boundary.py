"""Edge-identity boundary probe for A1's `CHUNK_DUPLICATE_EDGE` repair
(missions PEP-A3-SUSTAINED-013 slice 2: duplicate/malformed AST relationships,
and slice 5: no regression introduced by the repair).

The repair refuses two children sharing `(parentId, role, childIndex)`. Two
failure modes matter and only one of them is the original defect:

  * FAIL-OPEN (the original IDX3 defect): the duplicate edge is accepted.
  * OVER-REFUSAL (a new defect the repair could introduce): a **real parse** of
    a real program is refused by the index, i.e. the repair rejects legitimate
    documents. This probe measures that directly instead of assuming the check
    is safe.

Claims:
  E0  every example that parses at this pin also builds a `DocumentIndex`
      (non-regression against real parses).
  E1  an exact duplicate child edge is refused (`CHUNK_DUPLICATE_EDGE` or the
      declared `CHUNK_DUPLICATE_NODE`).
  E2  a duplicate edge whose only difference is `kind`/`text` is still refused —
      identity is the edge, not the payload. Asserted only when E1's refusal
      exists, so it cannot be vacuous on an unpatched pin.
  Observations (not claims): how many nodes the real examples yield, which of
  `(parentId, role, childIndex)` / `(parentId, childIndex)` are unique per
  parent in real parses (this is A1's premise, measured), whether a negative
  document-level `childIndex` is refused at index level, and any example that
  cannot be parsed inside the host parser limits (bounded, labelled SKIP).

Pure index/parser layer: no emission, no native build, no execution.
Exit codes: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python edge_identity_boundary.py <pinned-worktree>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import ContractRefusal, DocumentIndex  # noqa: E402

RESULTS = []
ACCEPTED_CODES = ("CHUNK_DUPLICATE_EDGE", "CHUNK_DUPLICATE_NODE")


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
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def index_with(nodes):
    return DocumentIndex("doc-edge", "rev-edge", nodes)


def open_parser_tools(session):
    bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "a3-edge-bundle", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "a3-edge-vectors", "bytes": []})
    require(sample, "outcome", "ok", "open validation sample")
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
    finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                  done=True, lex_done=True, lex_stage="done")
    for tool, function, arguments, expected in [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor))]:
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_register", "tool": tool,
                                   "document": opened["document"],
                                   "revision": opened["revision"], "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": opened["document"],
                                  "revision": opened["revision"],
                                  "testVectors": [{"arguments": arguments, "expect": expected,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": tool,
                                  "document": opened["document"],
                                  "revision": opened["revision"]})
        require(activated, "status", "Active", f"activate {tool}")
    return opened["revision"]


def real_example_scan():
    """Parse every example and check the repair does not refuse a real parse."""
    examples = sorted((REPO / "examples").glob("*.pep"))
    rows, refusals, unparsed = [], [], []
    edge_dupes, childindex_dupes = 0, 0
    session = Session()
    try:
        tool_revision = open_parser_tools(session)
        for path in examples:
            source_bytes = path.read_bytes()
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"a3-edge-{path.stem}", "bytes": list(source_bytes)})
            if target.get("outcome") != "ok":  # source-open cap: bounded skip, no verdict
                unparsed.append({"example": path.name,
                                 "reason": "open refused: "
                                           + str((target.get("error") or {}).get("code"))})
                continue
            try:
                parsed = parse_target(session, source_bytes, target, tool_revision)
            except BaseException as error:  # bounded parser limits, not a verdict
                unparsed.append({"example": path.name,
                                 "reason": f"{type(error).__name__}: {error}"[:160]})
                continue
            try:
                index = DocumentIndex.from_parsed(parsed)
            except ContractRefusal as refusal:
                refusals.append({"example": path.name, "code": refusal.code,
                                 "message": refusal.detail})
                continue
            nodes = index.nodes
            seen_edges, seen_child = set(), set()
            for node in nodes:
                fields = {field["name"]: field["value"]["value"] for field in node["fields"]}
                edge = (fields["parentId"], fields["role"], fields["childIndex"])
                child = (fields["parentId"], fields["childIndex"])
                if edge in seen_edges:
                    edge_dupes += 1
                seen_edges.add(edge)
                if child in seen_child:
                    childindex_dupes += 1
                seen_child.add(child)
            rows.append({"example": path.name, "nodes": len(nodes),
                         "index": "built"})
    finally:
        session.close()
    record("E0 real example parses build a DocumentIndex (no over-refusal)", True,
           "every parsed example builds an index",
           "every parsed example builds an index" if not refusals else "OVER_REFUSED",
           f"built={len(rows)} refused={json.dumps(refusals)[:400]} "
           f"unparsed({len(unparsed)})={[item['example'] for item in unparsed]}")
    RESULTS.append({"case": "O1 real-parse key uniqueness (observation)", "claimed": False,
                    "expect": "observed",
                    "outcome": f"edge_dupes={edge_dupes} childindex_dupes={childindex_dupes}",
                    "detail": json.dumps(rows), "falsified": False})
    print(f"[O1] observation: duplicate edges in real parses={edge_dupes}, "
          f"duplicate (parent,childIndex) pairs={childindex_dupes}")
    return refusals


def main():
    print(f"REPO={REPO}")
    refusals = real_example_scan()

    # ---- E1: the exact duplicate edge (the original IDX3 defect) -------------
    try:
        index_with([flat_node(0, -1, 0, role="", kind="function"),
                    flat_node(1, 0, 0, role="statement", kind="let"),
                    flat_node(2, 0, 0, role="statement", kind="let")])
    except ContractRefusal as refusal:
        # outcome carries only "refused"; the exact code and detail go in `detail`,
        # so a correct refusal can never be scored as a failure by a string mismatch.
        if refusal.code in ACCEPTED_CODES:
            record("E1 exact duplicate edge refused", True, "refused", "refused",
                   f"{refusal.code}: {refusal.detail}"[:200])
        else:
            record("E1 exact duplicate edge refused", True, "refused",
                   f"refused with undeclared {refusal.code}",
                   f"{refusal.code}: {refusal.detail}"[:200])
    else:
        record("E1 exact duplicate edge refused", True, "refused",
               "ACCEPTED (fail-open)", "")

    # ---- E2: identity is the edge, not the payload ---------------------------
    try:
        index_with([flat_node(0, -1, 0, role="", kind="function"),
                    flat_node(1, 0, 0, role="statement", kind="let", text="a"),
                    flat_node(2, 0, 0, role="statement", kind="return", text="b")])
    except ContractRefusal as refusal:
        record("E2 duplicate edge with different kind/text still refused", True,
               "refused", "refused", f"{refusal.code}: {refusal.detail}"[:200])
    else:
        record("E2 duplicate edge with different kind/text still refused", True,
               "refused", "ACCEPTED (identity treated as content)", "")

    # ---- O2: distinct edges are not conflated -------------------------------
    cases = {
        "same parent+childIndex, different role": [
            flat_node(0, -1, 0, role="", kind="function"),
            flat_node(1, 0, 0, role="statement", kind="let"),
            flat_node(2, 0, 0, role="then-branch", kind="return")],
        "same parent+role, different childIndex": [
            flat_node(0, -1, 0, role="", kind="function"),
            flat_node(1, 0, 0, role="statement", kind="let"),
            flat_node(2, 0, 1, role="statement", kind="return")],
    }
    for name, nodes in cases.items():
        try:
            index_with(nodes)
            outcome = "accepted"
        except ContractRefusal as refusal:
            outcome = f"refused {refusal.code}"
        RESULTS.append({"case": f"O2 distinct edges accepted ({name})", "claimed": False,
                        "expect": "observed", "outcome": outcome, "detail": "",
                        "falsified": False})
        print(f"[O2] {name}: {outcome}")

    # ---- O3: document-level negative childIndex ------------------------------
    try:
        index_with([flat_node(0, -1, 0), flat_node(1, 0, -1)])
        outcome = "accepted at index level"
    except ContractRefusal as refusal:
        outcome = f"refused {refusal.code}"
    RESULTS.append({"case": "O3 document-level negative childIndex", "claimed": False,
                    "expect": "observed", "outcome": outcome, "detail": "",
                    "falsified": False})
    print(f"[O3] negative childIndex at index level: {outcome}")

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
