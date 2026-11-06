"""A1 utf8_check headroom trial: baseline measurement probe (read-only).

Derived from tests/test_lexer_chunk_ledger.py machinery verbatim (same staging,
same chunk plan), plus two additions the ledger does not report:

  1. Per-invocation checker steps via pep_ocaml.ml's READ-ONLY
     metrics.last_execute_steps counter (added at 3ff3bf1; any peer can
     reproduce without instrumenting the tree).
  2. A diagnostics fingerprint per chunk (status + sorted diagnostic (code,
     message) pairs), written to a JSON file so a source-identity check can be
     done after the trial refactor.

Nothing writes inside the session; budgets and diagnostics are unchanged.
Usage:
  python tests/probe_utf8_headroom.py [--out _build/utf8_baseline.json]
"""
import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import pep_c23
import pep_chunk_contract as contract
from pep_c23 import Session, parse_target, require
from chunk_helper import fields_map
from tests.chunk_helper import (checked_fn_value, decl_closure, fetch_all_sigs,
                                 nval, remap_chunk, resolved_sig_value,
                                 variant_to_union)

NL = chr(10)


def main():
    source_path = ROOT / "examples" / "pep_lexer.pep"
    source_name = "utf8-headroom"
    out_path = ROOT / "_build" / "utf8_baseline.json"
    argv = sys.argv[1:]
    if "--source" in argv:
        i = argv.index("--source")
        source_path = pathlib.Path(argv[i + 1])
        source_name = source_path.stem
        argv = argv[:i] + argv[i + 2:]
    if "--out" in argv:
        i = argv.index("--out")
        out_path = pathlib.Path(argv[i + 1])
    session = Session()
    bundle = NL.join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "pep-c23", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    tool_revision = opened["revision"]
    tool_document = opened["document"]
    sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "validate", "bytes": []})
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
    empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
    empty_ext = {"type": "List[CheckedFunction]", "value": []}
    empty_sig = {"type": "List[ResolvedSignature]", "value": []}
    start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
    finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                  done=True, lex_done=True, lex_stage="done")
    tool_functions = {"pep-c23-parser-start": "parser_start",
                      "pep-c23-parser-step": "parser_step",
                      "pep-c23-checker-chunk": "analyze_chunk",
                      "pep-c23-checker-sigs": "chunk_signatures"}
    tool_args = {"pep-c23-parser-start": ([], start_cursor),
                 "pep-c23-parser-step": ([finished_cursor],
                     pep_c23.parser_chunk_value(sample["document"], sample["revision"], finished_cursor)),
                 "pep-c23-checker-chunk": ([empty_pp, empty_ext, empty_sig], empty_rep),
                 "pep-c23-checker-sigs": ([empty_pp], empty_sig)}
    for tool, function in tool_functions.items():
        arguments, expected = tool_args[tool]
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                      "tool": tool, "document": tool_document,
                      "revision": tool_revision, "function": function})
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": tool_document, "revision": tool_revision,
                                  "testVectors": [{"arguments": arguments, "expect": expected,
                                                   "semanticTarget": target_spec}]})
        require(validated, "outcome", "ok", f"validate {tool}")
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                      "tool": tool, "document": tool_document, "revision": tool_revision})

    source_bytes = source_path.read_bytes()
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": source_name, "bytes": list(source_bytes)})
    require(target, "outcome", "ok", "open lexer")
    sem = {"document": target["document"], "revision": target["revision"],
           "entryFunctions": []}
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

    report_rows = {}
    for position, label in enumerate(labels):
        planned = plan.node_ids(position)
        chunk_nodes = index.nodes_for(planned)
        other = [sig for sig in sigs if int(sig["node"]) not in set(planned)]
        sliced = {"type": "ParserProgress",
                  "fields": [{"name": key,
                              "value": ({"type": "List[FlatAstNode]",
                                         "value": remap_chunk(copy.deepcopy(chunk_nodes))}
                                        if key == "nodes" else fields_map(parsed)[key])}
                             for key in [f["name"] for f in parsed["fields"]]]}
        try:
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke",
                                     "tool": "pep-c23-checker-chunk",
                                     "arguments": [sliced,
                                                   {"type": "List[CheckedFunction]",
                                                    "value": [checked_fn_value(sig) for sig in other]},
                                                   {"type": "List[ResolvedSignature]",
                                                    "value": [resolved_sig_value(sig) for sig in other]}],
                                     "semanticTarget": sem})
        except RuntimeError as error:
            # Same contract as the ledger harness: a per-message transport refusal is
            # a measurement ("host-transport-limit"), never a crash.
            metrics = session.send({"schemaVersion": 3, "op": "metrics"}).get("metrics", {})
            report_rows[label] = {"status": "host-transport-limit",
                                  "steps": metrics.get("last_execute_steps"),
                                  "nodes": len(planned), "detail": str(error)[:120]}
            continue
        metrics = session.send({"schemaVersion": 3, "op": "metrics"}).get("metrics", {})
        steps = metrics.get("last_execute_steps")
        if response.get("outcome") != "ok":
            code = (response.get("error") or {}).get("code")
            report_rows[label] = {"status": code, "steps": steps, "nodes": len(planned)}
            continue
        rep = response["result"]
        fm = fields_map(rep)
        diags = sorted(tuple(sorted(d.get("fields", []), key=lambda x: x["name"]))
                       for d in (fm.get("diagnostics", {}).get("value") or []))
        report_rows[label] = {"status": fm["status"]["value"], "steps": steps,
                              "nodes": len(planned),
                              "diagnostics": json.dumps(diags, sort_keys=True)[:400]}

    result = {"labels": labels, "rows": report_rows}
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for label in labels:
        row = report_rows[label]
        print(f"{label:34s} {str(row['status']):26s} steps={row['steps']}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
