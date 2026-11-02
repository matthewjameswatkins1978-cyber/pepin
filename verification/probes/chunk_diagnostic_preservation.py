"""Agent 3 cross-chunk DIAGNOSTIC PRESERVATION probe (Lucy advisory: diagnostic
preservation + cross-chunk diagnostics), v2.

v1 of this probe compared a multi-error whole-source query against the chunked
union and was DISCARDED before commit: the seed's whole-source path reports the
FIRST error only (corpus S2), so that comparison was ill-posed. v2 isolates one
error per fixture so each path yields exactly one diagnostic to compare.

Reference: whole-source session `query` (plain dicts; {code, message, byte span})
vs `analyze_chunk` reports from the staged chunked path (transport
`CheckDiagnostic` {code, message, syntaxId, startByte, endByte}), same document,
same revision, no edits, one deliberate local error per fixture.

Claims (aggregated over all fixtures):
  VAC   each single-error fixture yields exactly one whole-source diagnostic
        (non-vacuity: guards the comparisons below).
  CD1   no LOSS — every whole-source (code, startByte, endByte) is reproduced by
        the chunk that carries those bytes (codes + spans are this project's
        differential standard).
  CD2   no EXTRAS/duplicates — every chunked (code, startByte, endByte) exists
        in the whole-source list (a span reported by two chunks fires this).
  CD3   MESSAGE PARITY — the matching chunked diagnostic carries the same
        message text as the whole-source path (same error, same words; message
        text is asserted by this repo's own tests).

Observations: per-chunk assignment; spans outside the reporting chunk's node
byte intervals (leakage); whole/chunked counts per fixture.

Pure checker/session layer; no emission, no native build, no execution.
Exit code: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python chunk_diagnostic_preservation.py <repo-root-at-pin>
"""
import copy
import json
import pathlib
import sys
from collections import Counter

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import (checked_fn_value, decl_closure, fetch_all_sigs,  # noqa: E402
                                fields_map, nval, remap_chunk, resolved_sig_value,
                                variant_to_union)

RESULTS = []
PER_FIXTURE = {}

FIXTURES = {
    "decl_only": "type Box { f: Nope }\nfn main() -> Int { return 0 }\n",
    "alpha_only": ("fn alpha() -> Int {\n"
                   "  let a: Zzz = 1\n"
                   "  return 0\n"
                   "}\n"
                   "fn main() -> Int { return alpha() }\n"),
    "beta_only": ("fn beta() -> Int {\n"
                  "  return Qqq\n"
                  "}\n"
                  "fn main() -> Int { return beta() }\n"),
}


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def whole_diagnostics(query_response):
    out = []
    for item in query_response.get("diagnostics") or []:
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
    spans = []
    for node in nodes:
        f = fields_map(node)
        spans.append((int(f["startByte"]["value"]), int(f["endByte"]["value"])))
    return spans


def analyse_fixture(session, tool_revision, name, source):
    source_bytes = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": f"chunk-diag-{name}", "bytes": list(source_bytes)})
    require(target, "outcome", "ok", f"open {name}")
    sem = {"document": target["document"], "revision": target["revision"],
           "entryFunctions": []}
    whole = session.send({"schemaVersion": 3, "op": "query",
                          "document": target["document"],
                          "revision": target["revision"]})
    whole_list = whole_diagnostics(whole)

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
                       and nval(node, "kind") in ("record_declaration", "union_declaration")}
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

    chunked, per_chunk, leakage = [], {}, []
    for position, label in enumerate(labels):
        planned = plan.node_ids(position)
        chunk_nodes = index.nodes_for(planned)
        intervals = node_intervals(chunk_nodes)
        other = [sig for sig in sigs if int(sig["node"]) not in set(planned)]
        sliced = {"type": "ParserProgress", "fields": [
            {"name": key, "value": ({"type": "List[FlatAstNode]",
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
            record(f"{name}: chunk {label} analysed", False, "observed", "INVOKE_ERROR",
                   json.dumps(response.get("error"))[:200])
            continue
        diags = transport_diagnostics(response["result"])
        per_chunk[label] = diags
        for entry in diags:
            chunked.append(entry)
            if not any(lo <= entry[2] and entry[3] <= hi for lo, hi in intervals):
                leakage.append((label,) + entry)
    return whole_list, chunked, per_chunk, leakage


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-chunk-diag", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]

        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v", "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
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
            reg = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_register", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "function": function})
            require(reg, "status", "Registered", f"register {tool}")
            val = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_validate", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "testVectors": [{"arguments": arguments, "expect": expected,
                                                 "semanticTarget": target_spec}]})
            require(val, "status", "Validated", f"validate {tool}")
            act = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_activate", "tool": tool,
                                "document": tool_document, "revision": tool_revision})
            require(act, "status", "Active", f"activate {tool}")

        for name, source in FIXTURES.items():
            whole_list, chunked, per_chunk, leakage = analyse_fixture(
                session, tool_revision, name, source)
            PER_FIXTURE[name] = {"whole": whole_list, "chunked": chunked,
                                 "per_chunk": per_chunk, "leakage": leakage}

        # ---- aggregate claims -------------------------------------------------
        vac_bad = {n: len(v["whole"]) for n, v in PER_FIXTURE.items()
                   if len(v["whole"]) != 1}
        record("VAC each single-error fixture yields exactly one whole-source "
               "diagnostic", True, "all-one", "all-one" if not vac_bad else "vacuous",
               json.dumps({n: len(v["whole"]) for n, v in PER_FIXTURE.items()}))

        lost = {}
        extra = {}
        message_mismatch = {}
        for name, data in PER_FIXTURE.items():
            whole_keys = Counter((c, s, e) for c, _, s, e in data["whole"])
            chunk_keys = Counter((c, s, e) for c, _, s, e in data["chunked"])
            miss = whole_keys - chunk_keys
            ext = chunk_keys - whole_keys
            if miss:
                lost[name] = sorted(miss.elements())
            if ext:
                extra[name] = sorted(ext.elements())
            for c, m, s, e in data["whole"]:
                mates = [(cc, mm, ss, ee) for cc, mm, ss, ee in data["chunked"]
                         if (cc, ss, ee) == (c, s, e)]
                if mates and all(mm != m for _, mm, _, _ in mates):
                    message_mismatch[name] = {"whole": (c, m, s, e),
                                              "chunked": [mm for _, mm, _, _ in mates]}
        record("CD1 no LOSS: every whole-source (code, span) is reproduced by the "
               "chunked path", True, "none-lost",
               "none-lost" if not lost else "loss", json.dumps(lost))
        record("CD2 no EXTRAS/duplicates across chunks", True, "none-extra",
               "none-extra" if not extra else "extras", json.dumps(extra))
        record("CD3 message parity for the same (code, span)", True, "messages-equal",
               "messages-equal" if not message_mismatch else "messages-differ",
               json.dumps(message_mismatch, ensure_ascii=False))

        # ---- observations -----------------------------------------------------
        record("O1 per-fixture whole/chunked diagnostics + chunk assignment", False,
               "observed",
               json.dumps({n: {"whole": v["whole"], "chunked": v["chunked"],
                               "per_chunk": {k: d for k, d in v["per_chunk"].items()}}
                           for n, v in PER_FIXTURE.items()}, ensure_ascii=False),
               "")
        leaks = {n: v["leakage"] for n, v in PER_FIXTURE.items() if v["leakage"]}
        record("O2 spans outside the reporting chunk's node byte intervals (leakage)",
               False, "observed", json.dumps(leaks), "")
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


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
