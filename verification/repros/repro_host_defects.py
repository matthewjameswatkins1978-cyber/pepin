"""Agent 3 minimal standalone repros for the host product defects handed to A1
(LUCY-20261103-012: "reconstruct minimal reproducible ... hand exact repro and
expected codes to A1"), plus the CD3 message-parity decision baseline.

Each case is deliberately small, prints EXPECTED vs ACTUAL, and never hides a
harness failure as a result:

  IDX3   Two distinct siblings carrying the SAME (parentId, role, childIndex)
         edge must be refused when the document index is built. The contract
         treats that triple as a child key (child_at / count_children / emitter
         fixed-slot routing), and no authoritative parse can contain two
         children with one edge identity.
         EXPECTED: refusal at DocumentIndex construction, declared code
         CHUNK_DUPLICATE_NODE (preferred: same identity class, no new contract
         surface) or a newly declared CHUNK_DUPLICATE_EDGE.
  STALE1 Arguments derived from revision rev1 presented under a semanticTarget
         at the advanced rev2 must be REFUSED (describe publishes
         crossRevisionReuse: false; provenance from one revision may never
         answer under another).
         EXPECTED: outcome=error with a declared stale/provenance code, e.g.
         PEP_SEMANTIC_TARGET_STALE. Never outcome=ok, and never an empty report
         wearing the target revision's label.
  CD3    One deliberate error per fixture: the same (code, UTF-8 byte span) must
         carry the same message text on the whole-source (seed) and chunked
         (Pep-written checker) paths.
         EXPECTED: message equality for every fixture diagnostic.

Usage:
  python verification/repros/repro_host_defects.py <pinned-worktree> [IDX3 STALE1 CD3]

Exit codes:
  0 = every expectation holds (defect absent at this pin)
  1 = at least one defect reproduced or expectation mismatched
  2 = harness error (never silently reported as a defect)

This file is Agent 3 verification-owned; it runs against a pinned worktree and
changes nothing in it.
"""
import copy
import json
import pathlib
import sys

ARGS = [item for item in sys.argv[1:] if not item.startswith("-")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
WANTED = {item.upper() for item in ARGS[1:]} or {"IDX3", "STALE1", "CD3"}
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from pep_chunk_contract import ContractRefusal, DocumentIndex  # noqa: E402

RESULTS = []

# One deliberate type error: unknown type `Zzz`.
BASE_SOURCE = ("fn main() -> Int {\n"
               "  let x: Zzz = 1\n"
               "  return 0\n"
               "}\n")

# Single-error fixtures: the seed reports only the FIRST error per source, so one
# error per fixture keeps the two paths comparable.
CD3_FIXTURE = "type Box { f: Nope }\nfn main() -> Int { return 0 }\n"


def scalar(type_name, value):
    return {"type": type_name, "value": value}


def flat_node(node_id, parent_id, child_index=0, role="statement", kind="name", text=""):
    """One transport-shape FlatAstNode (same field order the host emits)."""
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


def record(case, expected, actual, verdict, detail=""):
    RESULTS.append({"case": case, "expected": expected, "actual": actual,
                    "verdict": verdict, "detail": detail})
    print(f"\n[{case}] {verdict}")
    print(f"  EXPECTED: {expected}")
    print(f"  ACTUAL  : {actual}")
    if detail:
        print(f"  DETAIL  : {detail}")


def register_tool(session, tool, function, arguments, expect, target_spec,
                  tool_document, tool_revision):
    """tool_register -> tool_validate -> tool_activate for one v2 tool."""
    registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_register", "tool": tool,
                               "document": tool_document, "revision": tool_revision,
                               "function": function})
    require(registered, "status", "Registered", f"register {tool}")
    validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": tool,
                              "document": tool_document, "revision": tool_revision,
                              "testVectors": [{"arguments": arguments, "expect": expect,
                                               "semanticTarget": target_spec}]})
    require(validated, "status", "Validated", f"validate {tool}")
    activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": tool,
                              "document": tool_document, "revision": tool_revision})
    require(activated, "status", "Active", f"activate {tool}")


def open_bundle(session):
    """Compile the four Pep sources and return (tool_document, tool_revision,
    validation semanticTarget) for tool registration."""
    bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "a3-repro-bundle", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "a3-repro-vectors", "bytes": []})
    require(sample, "outcome", "ok", "open validation sample")
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    return opened["document"], opened["revision"], target_spec, sample


def register_parser_tools(session, tool_document, tool_revision, target_spec, sample):
    start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
    finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                  done=True, lex_done=True, lex_stage="done")
    register_tool(session, "pep-c23-parser-start", "parser_start", [], start_cursor,
                  target_spec, tool_document, tool_revision)
    register_tool(session, "pep-c23-parser-step", "parser_step", [finished_cursor],
                  pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                             finished_cursor),
                  target_spec, tool_document, tool_revision)


# --------------------------------------------------------------------------
# IDX3 — duplicate child edge
# --------------------------------------------------------------------------
IDX3_PREFERRED = "CHUNK_DUPLICATE_NODE"
IDX3_ALTERNATE = "CHUNK_DUPLICATE_EDGE"


def case_idx3():
    nodes = [flat_node(0, -1, 0, role="", kind="function", text="f"),
             flat_node(1, 0, 0, role="statement", kind="let"),
             flat_node(2, 0, 0, role="statement", kind="let")]
    expected = (f"refusal at DocumentIndex construction with {IDX3_PREFERRED} "
                f"(or declared {IDX3_ALTERNATE})")
    try:
        DocumentIndex("doc-idx3", "rev-idx3", nodes)
    except ContractRefusal as refusal:
        if refusal.code in (IDX3_PREFERRED, IDX3_ALTERNATE):
            record("IDX3", expected, f"refused {refusal.code}", "HELD",
                   "no fail-open; contract surface declared")
        else:
            record("IDX3", expected, f"refused {refusal.code}", "MISMATCH",
                   "fail-open fixed but the code is not declared for this class")
    else:
        record("IDX3", expected, "ACCEPTED (index built over duplicate edge)", "DEFECT",
               "two children share (parent=0, role=statement, childIndex=0)")


# --------------------------------------------------------------------------
# STALE1 — crossed provenance (rev1 arguments under rev2 semanticTarget)
# --------------------------------------------------------------------------
STALE_OK_CODES = ("PEP_SEMANTIC_TARGET_STALE", "PEP_TOOL_STALE_REVISION",
                  "CHUNK_STALE_REVISION", "PEP_STALE_REVISION",
                  "PEP_SEMANTIC_TARGET_MISMATCH")


def type_fields(value):
    return {field["name"]: field["value"] for field in value["fields"]}


def case_stale1():
    session = Session()
    try:
        tool_document, tool_revision, target_spec, sample = open_bundle(session)
        register_parser_tools(session, tool_document, tool_revision, target_spec, sample)
        empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        register_tool(session, "pep-c23-checker", "analyze_parsed", [empty_parsed],
                      empty_checked, target_spec, tool_document, tool_revision)

        source_bytes = BASE_SOURCE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "stale-target", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open stale target")
        document, rev1 = target["document"], target["revision"]
        sem1 = {"document": document, "revision": rev1, "entryFunctions": []}
        parsed1 = parse_target(session, source_bytes, target, tool_revision)

        control = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed1], "semanticTarget": sem1})
        if control.get("outcome") != "ok":
            raise RuntimeError(f"control invoke on the matching pair failed: {control}")

        advance = session.send({"schemaVersion": 3, "op": "apply_edit",
                                "document": document, "expected_revision": rev1,
                                "start_byte": 0, "end_byte": 0, "replacement": "//x\n"})
        require(advance, "outcome", "ok", "advance target revision")
        rev2 = advance["revision"]
        if rev2 == rev1:
            raise RuntimeError("target revision did not advance")

        crossed = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed1],
                                "semanticTarget": {"document": document,
                                                   "revision": rev2,
                                                   "entryFunctions": []}})
        expected = ("outcome=error with a declared stale/provenance code "
                    f"({', '.join(STALE_OK_CODES)})")
        if crossed.get("outcome") == "error":
            code = (crossed.get("error") or {}).get("code", "NO_CODE")
            verdict = "HELD" if code in STALE_OK_CODES else "MISMATCH"
            record("STALE1", expected, f"refused {code}", verdict,
                   "crossed provenance refused before the tool ran"
                   if verdict == "HELD" else
                   "refused, but the code is not in the declared stale family")
        else:
            fields = type_fields(crossed["result"])
            declared = (fields.get("revision") or {}).get("value")
            node_count = (fields.get("syntaxNodeCount") or {}).get("value")
            record("STALE1", expected,
                   f"outcome=ok (report revision={declared}, syntaxNodeCount={node_count})",
                   "DEFECT",
                   f"rev1-derived arguments answered under rev2={rev2[:12]}…: "
                   f"declared revision follows the target label, node count is not the "
                   f"analysed data; expected refusal, got a report")
    finally:
        session.close()


# --------------------------------------------------------------------------
# CD3 — message parity between whole-source and chunked diagnostics
# --------------------------------------------------------------------------
def case_cd3():
    from tests.chunk_helper import (checked_fn_value, decl_closure, fetch_all_sigs,
                                    fields_map, nval, remap_chunk, resolved_sig_value,
                                    variant_to_union)

    def whole_diagnostics(response):
        out = []
        for item in response.get("diagnostics") or []:
            span = item.get("span", {})
            start = span.get("start") or {}
            out.append((item.get("code"), item.get("message"),
                        int(start.get("offset", -1)), int(span.get("endOffset", -1))))
        return out

    def transport_diagnostics(report):
        raw = fields_map(report).get("diagnostics", {})
        items = raw.get("value", []) if isinstance(raw, dict) else raw
        out = []
        for item in items:
            fields = fields_map(item)
            out.append((fields.get("code", {}).get("value"),
                        fields.get("message", {}).get("value"),
                        int(fields.get("startByte", {}).get("value", -1)),
                        int(fields.get("endByte", {}).get("value", -1))))
        return out

    def node_intervals(nodes):
        return [(int(fields_map(node)["startByte"]["value"]),
                 int(fields_map(node)["endByte"]["value"])) for node in nodes]

    session = Session()
    try:
        tool_document, tool_revision, target_spec, sample = open_bundle(session)
        register_parser_tools(session, tool_document, tool_revision, target_spec, sample)
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        register_tool(session, "pep-c23-checker-chunk", "analyze_chunk",
                      [empty_pp, empty_ext, empty_sig], empty_rep,
                      target_spec, tool_document, tool_revision)
        register_tool(session, "pep-c23-checker-sigs", "chunk_signatures", [empty_pp],
                      empty_sig, target_spec, tool_document, tool_revision)

        source_bytes = CD3_FIXTURE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "cd3-fixture", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open CD3 fixture")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        whole = whole_diagnostics(session.send(
            {"schemaVersion": 3, "op": "query", "document": target["document"],
             "revision": target["revision"]}))

        parsed = parse_target(session, source_bytes, target, tool_revision)
        nodes = fields_map(parsed)["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        by_id = {str(nval(node, "id")): node for node in nodes}
        sigs = fetch_all_sigs(session, parsed, tool_revision, sem)
        sigs_by_name = {sig["name"]: sig for sig in sigs}
        functions = [node for node in nodes if nval(node, "kind") == "function"
                     and str(nval(node, "parentId")) == "-1"]
        declaration_roots = [int(nval(node, "id")) for node in nodes
                             if str(nval(node, "parentId")) == "-1"
                             and nval(node, "kind") != "function"]
        decl_name_to_id = {nval(node, "text"): str(nval(node, "id")) for node in nodes
                           if str(nval(node, "parentId")) == "-1"
                           and nval(node, "kind") in ("record_declaration",
                                                      "union_declaration")}
        v2u = variant_to_union(nodes)

        chunk_ids, labels = [], []
        for root in declaration_roots:
            chunk_ids.append(sorted(index.subtree(root)))
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
        chunked = []
        for position, label in enumerate(labels):
            planned = plan.node_ids(position)
            chunk_nodes = index.nodes_for(planned)
            intervals = node_intervals(chunk_nodes)
            other = [sig for sig in sigs if int(sig["node"]) not in set(planned)]
            sliced = {"type": "ParserProgress", "fields": [
                {"name": key,
                 "value": ({"type": "List[FlatAstNode]",
                            "value": remap_chunk(copy.deepcopy(chunk_nodes))}
                           if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                     "arguments": [sliced,
                                                   {"type": "List[CheckedFunction]",
                                                    "value": [checked_fn_value(sig)
                                                              for sig in other]},
                                                   {"type": "List[ResolvedSignature]",
                                                    "value": [resolved_sig_value(sig)
                                                              for sig in other]}],
                                     "semanticTarget": sem})
            if response.get("outcome") != "ok":
                raise RuntimeError(f"chunk {label} invoke failed: {response.get('error')}")
            for entry in transport_diagnostics(response["result"]):
                if not any(lo <= entry[2] and entry[3] <= hi for lo, hi in intervals):
                    raise RuntimeError(f"chunk {label} reported a span outside its nodes: "
                                       f"{entry}")
                chunked.append((label,) + entry)

        if len(whole) != 1 or len(chunked) != 1:
            raise RuntimeError(f"non-vacuity: expected exactly one diagnostic per path, "
                               f"got whole={whole} chunked={chunked}")

        whole_code, whole_message, whole_start, whole_end = whole[0]
        label, chunk_code, chunk_message, chunk_start, chunk_end = chunked[0]
        expected = (f"same message for identical (code, span): "
                    f"{whole_code} {whole_start}-{whole_end}")
        actual = (f"whole={whole_message!r} "
                  f"chunked({label})={chunk_message!r}")
        if (whole_code, whole_start, whole_end) != (chunk_code, chunk_start, chunk_end):
            record("CD3", expected, actual, "MISMATCH",
                   "codes/spans differ, so message parity is not yet the question — "
                   "report the identity divergence first")
        elif whole_message == chunk_message:
            record("CD3", expected, actual, "HELD", "message text matches")
        else:
            record("CD3", expected, actual, "DEFECT",
                   "same error, same bytes, different wording: either align the chunked "
                   "messages or declare chunk-contract messages outside the guarantee")
    finally:
        session.close()


def main():
    print(f"REPO={REPO}")
    print(f"CASES={sorted(WANTED)}")
    harness_error = None
    for name, runner in (("IDX3", case_idx3), ("STALE1", case_stale1), ("CD3", case_cd3)):
        if name not in WANTED:
            continue
        try:
            runner()
        except BaseException as error:  # harness failure must never read as a verdict
            import traceback
            traceback.print_exc()
            harness_error = f"{name}: {type(error).__name__}: {error}"
            print(f"\n[{name}] HARNESS_ERROR {harness_error}")
            break
    print("\n" + json.dumps({"repo": str(REPO),
                             "cases": RESULTS,
                             "harness_error": harness_error}, indent=2, sort_keys=True))
    if harness_error:
        return 2
    problem = [item for item in RESULTS if item["verdict"] != "HELD"]
    print(f"SUMMARY cases={len(RESULTS)} not_held={len(problem)}")
    for item in problem:
        print(f"NOT HELD: {item['case']} -> {item['verdict']} ({item['actual']})")
    return 1 if problem else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # pragma: no cover - harness guard
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
