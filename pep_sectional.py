"""A1 host sectional orchestration (experimental lane, LUCY-20261107-014).

Drives whole-file check+emit as bounded per-function tool calls and merges
the partial results host-side, so inputs larger than the 1 MiB / 10k-element
transport walls can still be checked and emitted without any cap, semantics,
or tool change. Pure orchestration over existing sectional entries
(`analyze_chunk_typed_bound`, `emit_c23_section`, `emit_c23_function_unit`).

Layering debt (recorded, not hidden): slice construction reuses
`tests.chunk_helper.remap_chunk` and host builtins come from
`tests.test_chunk_typed.host_builtins`; both belong in product code
(`pep_chunk_contract.py`) when this graduates. Entry point is
`build_c23`, wired to `pep_c23.py` as opt-in `--sectional`
(`emit(sectional=True)` keeps the one-shot path untouched by default).
"""
import copy
import json

import pep_chunk_contract as contract
from tests.chunk_helper import (checked_fn_value, fetch_all_sigs, fields_map,
                                nval, remap_chunk, resolved_sig_value, slice_subtree)


def _fval(elem, key):
    for f in elem.get("fields", []):
        if f["name"] == key:
            return f["value"].get("value")
    return None


def _fset(elem, key, newval):
    for f in elem.get("fields", []):
        if f["name"] == key:
            f["value"]["value"] = newval
            return


def sliced(parsed, node_ids):
    """ParserProgress for exactly these document-id nodes (remapped chunk-local)."""
    nodes = fields_map(parsed)["nodes"]["value"]
    by_id = {str(nval(n, "id")): n for n in nodes}
    sub = [copy.deepcopy(by_id[str(i)]) for i in node_ids]
    chunk = remap_chunk(sub)
    return {"type": "ParserProgress", "fields": [
        {"name": k, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                              if k == "nodes" else fields_map(parsed)[k])}
        for k in [field["name"] for field in parsed["fields"]]]}


def arg_bytes(arguments):
    return len(json.dumps(arguments, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")) + 1


def register_sectional_tools(session, tool_doc, tool_revision, sample, pep_c23):
    """Register parser + sigs + bound-chunk + section + unit tools (vectors from suites)."""
    doc, rev = sample["document"], sample["revision"]
    start_cursor = pep_c23.parser_cursor_value(doc, rev)
    finished_cursor = pep_c23.parser_cursor_value(
        doc, rev, done=True, lex_done=True, lex_stage="done")
    for tool, function, arguments, expect in [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(doc, rev, finished_cursor))]:
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_register", "tool": tool, "document": tool_doc,
                      "revision": tool_revision, "function": function})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_validate", "tool": tool, "document": tool_doc,
                      "revision": tool_revision,
                      "testVectors": [{"arguments": arguments, "expect": expect,
                                       "semanticTarget": {"document": doc,
                                                          "revision": rev,
                                                          "entryFunctions": []}}]})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_activate", "tool": tool, "document": tool_doc,
                      "revision": tool_revision})
    from pep_c23 import typed as typed_value
    empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
    empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
    refused = pep_c23.typed_record(
        "unsupported", (),
        "Pep C23 emission requires a top-level function named main")
    tools = [
        ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp],
         {"type": "List[ResolvedSignature]", "value": []}),
        ("pep-c23-section", "emit_c23_section",
         [empty_pp, empty_checked, typed_value("Str", "header")], refused),
        ("pep-c23-unit", "emit_c23_function_unit",
         [empty_pp, empty_checked, typed_value("Int", 0)], refused),
        # A2-S2 fragment entry (A3-113 registration vector: the empty
        # program is refused as out-of-range, which is the vector).
        ("pep-c23-frag", "emit_c23_statement_fragment",
         [empty_pp, empty_checked, typed_value("Int", 0),
          typed_value("Int", 0), typed_value("Int", 1)],
         pep_c23.typed_record("unsupported", (),
                              "Pep C23 function unit index is out of range")),
        ("bound-chunk", "analyze_chunk_typed_bound",
         [empty_pp,
          {"type": "List[CheckedFunction]", "value": []},
          {"type": "List[ResolvedSignature]", "value": []},
          {"type": "List[ResolvedTypeDecl]", "value": []},
          {"type": "List[BindingFact]", "value": []},
          {"type": "Bool", "value": True}], empty_checked),
    ]
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    for tool, function, arguments, expect in tools:
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_register", "tool": tool, "document": tool_doc,
                      "revision": tool_revision, "function": function})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_validate", "tool": tool, "document": tool_doc,
                      "revision": tool_revision,
                      "testVectors": [{"arguments": arguments, "expect": expect,
                                       "semanticTarget": target_spec}]})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                      "op": "tool_activate", "tool": tool, "document": tool_doc,
                      "revision": tool_revision})


def _invoke(session, tool, arguments, sem):
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": tool,
                             "arguments": arguments, "semanticTarget": sem})
    try:
        steps = session.send({"schemaVersion": 3, "op": "metrics"}).get(
            "metrics", {}).get("last_execute_steps")
    except Exception:  # noqa: BLE001 - metrics are best-effort
        steps = None
    return response, steps


def check_slice(session, sem, parsed, index, sigs, host, chunk_ids,
                expect_returns, bindings, entry_name):
    """One bound-chunk call: returns (raw_report_or_None, codes, steps, bytes)."""
    ext = [s for s in sigs if s["name"] != entry_name]
    allowed = index.fact_closure([int(i) for i in chunk_ids],
                                 {s["name"] for s in ext})
    ext = [s for s in ext if s["name"] in allowed]
    host_fns, host_sigs, host_types = host
    args = [sliced(parsed, [int(i) for i in chunk_ids]),
            {"type": "List[CheckedFunction]",
             "value": [checked_fn_value(s) for s in ext] + host_fns},
            {"type": "List[ResolvedSignature]",
             "value": [resolved_sig_value(s) for s in ext] + host_sigs},
            {"type": "List[ResolvedTypeDecl]", "value": host_types},
            {"type": "List[BindingFact]", "value": bindings},
            {"type": "Bool", "value": expect_returns}]
    nbytes = arg_bytes(args)
    resp, steps = _invoke(session, "bound-chunk", args, sem)
    if resp.get("outcome") != "ok":
        return None, [(resp.get("error") or {}).get("code")], steps, nbytes
    rep = fields_map(resp["result"])
    codes = sorted({fields_map(d)["code"]["value"]
                    for d in rep["diagnostics"]["value"]})[:3]
    if rep["status"]["value"] != "valid" or codes:
        return None, codes or [rep["status"]["value"]], steps, nbytes
    return resp["result"], [], steps, nbytes


def _carry_binding(pool, binding, g2s):
    """Admit one reported binding into a rank-space pool.

    New facts are translated from their chunk-local id to rank space via
    this group's g2s mapping (fail-closed on out-of-span), then pooled
    (dedupe + attestation by the pool). Echoes of already-admitted
    identities are verified against the pool's canonical payload and
    otherwise ignored: the pool's copy (rank space) is authoritative and
    echo field values are never adopted.
    """
    fields = {f["name"]: f["value"] for f in binding["fields"]}
    key, payload = contract.BindingPool._canonical(fields)
    if key in pool._seen:
        if pool._seen[key] != payload:
            raise ValueError(
                "sectional merge: conflicting carried binding")
        return
    b2 = copy.deepcopy(binding)
    skey = str(int(_fval(b2, "syntaxId")))
    if skey not in g2s:
        raise ValueError("sectional merge: binding outside slice span")
    _fset(b2, "syntaxId", g2s[skey])
    pool.add([b2])


def merge_reports(sliced_progress, groups, full_sorted, entry_name, all_fn_facts,
                  bindings=()):
    """Host-side union of per-group reports into one slice report.

    Group chunks are remapped independently, so syntaxIds are translated to
    the full-slice space by doc-id rank. References stay empty and holes
    must be absent; calls, functions, expressionTypes AND the carried
    bindings are the emitter's inputs (bindings feed A2's fragment entry:
    carried-name and assignment-target resolution). Functions follow the
    carried-facts recipe: local minted fact plus the whole-file functions
    list. Callers pass pool facts already translated to rank space; the
    merge re-checks every binding syntaxId against the rank span.

    Fail-closed (R3): every group report must carry the same document and
    revision (no stale/foreign facts), the group list must be non-empty,
    and every translated syntaxId must land inside the slice span.
    Violations raise ValueError — never silent adoption, never KeyError.
    """
    if not groups:
        raise ValueError("sectional merge: empty group list")
    want_doc = groups[0][1]["document"]
    want_rev = groups[0][1]["revision"]
    for _, rep in groups:
        if rep["document"] != want_doc:
            raise ValueError("sectional merge: foreign document in group")
        if rep["revision"] != want_rev:
            raise ValueError("sectional merge: stale revision in group")
    fields = fields_map(sliced_progress)
    nodes = fields["nodes"]["value"]
    rank = {str(doc): str(i) for i, doc in enumerate(full_sorted)}
    for _, rep in groups:
        if rep["holes"]["value"]:
            raise ValueError("sectional merge hit a hole; not supported")
    calls, fns, etypes = [], [], []
    seen_fn = set()
    # A3-080: scan ALL groups for the entry fact (the old double-break
    # took only groups[0]). Copies must agree on (name, semanticId); the
    # merged entry keeps the group copy (checker id-space, matching the
    # groups' own call facts), never silently first-wins.
    entry_keys = set()
    for _, rep in groups:
        for e in rep["functions"]["value"]:
            if _fval(e, "name") == entry_name:
                entry_keys.add((_fval(e, "name"), _fval(e, "semanticId")))
    if len(entry_keys) > 1:
        raise ValueError(
            "sectional merge: entry fact disagreement across groups")
    for _, rep in groups:
        for e in rep["functions"]["value"]:
            if _fval(e, "name") == entry_name:
                key = (_fval(e, "name"), _fval(e, "semanticId"))
                if key not in seen_fn:
                    seen_fn.add(key)
                    fns.append(copy.deepcopy(e))
                break
    for e in all_fn_facts:
        key = (_fval(e, "name"), _fval(e, "semanticId"))
        if key in seen_fn:
            continue
        seen_fn.add(key)
        fns.append(copy.deepcopy(e))
    for cids, rep in groups:
        order = [int(c) for c in cids]
        if order != sorted(order) or len(set(order)) != len(order):
            raise ValueError(
                "sectional merge: group ids not ascending-unique")
        ordered = sorted(order)
        g2s = {str(g): rank[str(doc)] for g, doc in enumerate(ordered)}
        for e in rep["calls"]["value"] + rep["expressionTypes"]["value"]:
            key = str(int(_fval(e, "syntaxId")))
            if key not in g2s:
                raise ValueError(
                    "sectional merge: group fact outside slice span")
        for e in rep["calls"]["value"]:
            c = copy.deepcopy(e)
            _fset(c, "syntaxId", g2s[str(int(_fval(e, "syntaxId")))])
            calls.append(c)
        for e in rep["expressionTypes"]["value"]:
            c = copy.deepcopy(e)
            _fset(c, "syntaxId", g2s[str(int(_fval(e, "syntaxId")))])
            etypes.append(c)
    # A3-080: every call must anchor in the merged function facts (the
    # emitter resolves calleeId/callerId by semanticId; a dangling id
    # means a foreign or forged fact). Single-group fully-consistent
    # forgery is definitionally valid input and stays the emitter's catch.
    allowed_ids = {str(_fval(e, "semanticId")) for e in fns}
    for c in calls:
        if str(_fval(c, "callerId")) not in allowed_ids or \
                str(_fval(c, "calleeId")) not in allowed_ids:
            raise ValueError(
                "sectional merge: call to unknown function fact")
    rank_values = set(rank.values())
    for b in bindings:
        key = str(int(_fval(b, "syntaxId")))
        if key not in rank_values:
            raise ValueError(
                "sectional merge: binding outside slice span")
    first = groups[0][1]
    return {"type": "CheckerReport", "fields": [
        {"name": "document", "value": first["document"]},
        {"name": "revision", "value": first["revision"]},
        {"name": "status", "value": {"type": "Str", "value": "valid"}},
        {"name": "syntaxNodeCount",
         "value": {"type": "Int", "value": str(len(nodes))}},
        {"name": "functions",
         "value": {"type": "List[CheckedFunction]", "value": fns}},
        {"name": "bindings",
         "value": {"type": "List[BindingFact]",
                   "value": [copy.deepcopy(b) for b in bindings]}},
        {"name": "references",
         "value": {"type": "List[ResolvedName]", "value": []}},
        {"name": "calls",
         "value": {"type": "List[ResolvedCall]", "value": calls}},
        {"name": "expressionTypes",
         "value": {"type": "List[ExpressionTypeFact]", "value": etypes}},
        {"name": "holes",
         "value": {"type": "List[HoleFact]", "value": []}},
        {"name": "diagnostics",
         "value": {"type": "List[CheckDiagnostic]", "value": []}}]}


def _duplicate_top_level_functions(nodes):
    """Names of top-level functions declared more than once (seed mirrors
    PEP_DUPLICATE_FUNCTION; the per-slice path checks each slice alone, so
    the host must refuse the shadow before any dict keying by name)."""
    seen, dupes = set(), []
    for n in nodes:
        if nval(n, "kind") == "function" and str(nval(n, "parentId")) == "-1":
            name = nval(n, "text")
            if name in seen and name not in dupes:
                dupes.append(name)
            seen.add(name)
    return dupes


def check_program(session, sem, parsed, tool_revision, target, host, sigs=None,
                  force_chain=frozenset()):
    """Sectional check of every top-level function.

    Returns dict: order, slices {name: progress}, reports {name: raw report},
    per-slice (steps, bytes), failures []. Fail-closed on first invalid.
    """
    nodes = fields_map(parsed)["nodes"]["value"]
    dupes = _duplicate_top_level_functions(nodes)
    if dupes:
        # A3-082 note 1: no caller reads sigs on the refusal path
        # (build_c23 raises on failures first), but return [] rather
        # than None so every return shape carries a list.
        return {"order": [], "slices": {}, "reports": {}, "stats": {},
                "failures": [(name, "duplicate-function",
                              ["PEP_DUPLICATE_FUNCTION"]) for name in dupes],
                "sigs": []}
    if sigs is None:
        sigs = fetch_all_sigs(session, parsed, tool_revision, sem)
    index = contract.DocumentIndex.from_parsed(parsed)
    fns = [n for n in nodes if nval(n, "kind") == "function"
           and str(nval(n, "parentId")) == "-1"]
    order = [nval(f, "text") for f in fns]
    all_fn_facts = [checked_fn_value(s) for s in sigs] + host[0]
    slices, reports, stats, failures = {}, {}, {}, []
    for fn in fns:
        name = nval(fn, "text")
        ids = [int(nval(n, "id")) for n in slice_subtree(nodes, nval(fn, "id"))]
        sl = sliced(parsed, ids)
        raw, codes, steps, nbytes = ((None, [], None, None)
                                     if name in force_chain else check_slice(
            session, sem, parsed, index, sigs, host, ids, True, [], name))
        if raw is not None:
            slices[name], reports[name] = sl, raw
            stats[name] = {"steps": steps, "bytes": nbytes, "mode": "whole"}
            continue
        # statement-group chain with carried bindings. Binding syntaxIds
        # are chunk-local per group report, so translate each group's facts
        # to rank space (same g2s mapping as calls/types) BEFORE pooling:
        # the pool dedupes by source-anchored identity and the emitter
        # reads pep_local_<rank-space syntaxId> from the merged report.
        pool = contract.BindingPool(target["document"], target["revision"])
        parts, ok = [], True
        full_sorted = sorted(int(i) for i in ids)
        rank = {str(doc): str(i) for i, doc in enumerate(full_sorted)}
        positions = index.statement_children(int(nval(fn, "id")))
        for pos in range(len(positions)):
            for label, cids, terminal in index.bounded_units(
                    int(nval(fn, "id")), groups=[("one", pos, pos + 1, (), False)]):
                if label != "one":
                    continue
                r2, c2, _, _ = check_slice(
                    session, sem, parsed, index, sigs, host,
                    list(cids), terminal, pool.facts(), name)
                if r2 is None:
                    ok = False
                    failures.append((name, pos, c2))
                    break
                parts.append((list(cids), fields_map(r2)))
                g2s = {str(g): rank[str(doc)]
                       for g, doc in enumerate(sorted(int(c) for c in cids))}
                for b in fields_map(r2)["bindings"]["value"]:
                    _carry_binding(pool, b, g2s)
            if not ok:
                break
        if not ok or len(parts) != len(positions):
            failures.append((name, "chain-incomplete", []))
            break
        reports[name] = merge_reports(sl, parts, full_sorted, name, all_fn_facts,
                                      bindings=pool.facts())
        slices[name] = sl
        stats[name] = {"steps": None, "bytes": None, "mode": f"chain-{len(parts)}"}
    return {"order": order, "slices": slices, "reports": reports,
            "stats": stats, "failures": failures, "sigs": sigs}


def emit_unit(session, sem, sl, report, index=0):
    """One function-unit emission: returns (status, diagnostic, parts, steps)."""
    from pep_c23 import typed as typed_value
    resp, steps = _invoke(session, "pep-c23-unit",
                           [sl, report, typed_value("Int", index)], sem)
    if resp.get("outcome") != "ok":
        return ("tool-error", (resp.get("error") or {}).get("code", ""), [], steps)
    fields = {item["name"]: item["value"] for item in resp["result"]["fields"]}
    parts = [p["value"] for p in fields["sourceParts"]["value"]]
    return (fields["status"]["value"], fields["diagnostic"]["value"], parts, steps)


def emit_section(session, sem, sl, report, part):
    """One named-section emission: returns (status, diagnostic, parts, steps)."""
    from pep_c23 import typed as typed_value
    resp, steps = _invoke(session, "pep-c23-section",
                           [sl, report, typed_value("Str", part)], sem)
    if resp.get("outcome") != "ok":
        return ("tool-error", (resp.get("error") or {}).get("code", ""), [], steps)
    fields = {item["name"]: item["value"] for item in resp["result"]["fields"]}
    parts = [p["value"] for p in fields["sourceParts"]["value"]]
    return (fields["status"]["value"], fields["diagnostic"]["value"], parts, steps)


def emit_fragment(session, sem, sl, report, function_index, first, count):
    """One statement-fragment emission: returns (status, diagnostic, parts, steps)."""
    from pep_c23 import typed as typed_value
    resp, steps = _invoke(session, "pep-c23-frag",
                           [sl, report, typed_value("Int", function_index),
                            typed_value("Int", first),
                            typed_value("Int", count)], sem)
    if resp.get("outcome") != "ok":
        return ("tool-error", (resp.get("error") or {}).get("code", ""), [], steps)
    fields = {item["name"]: item["value"] for item in resp["result"]["fields"]}
    parts = [p["value"] if isinstance(p, dict) else p
             for p in fields["sourceParts"]["value"]]
    return (fields["status"]["value"], fields["diagnostic"]["value"],
            parts, steps)


_C_TYPE_BY_NAME = {"Int": "int64_t", "Bool": "int64_t",
                    "SourceBytes": "pep_source_bytes"}


def build_fragmented_function(session, sem, sl, rep, name, sig_entry):
    """Assemble one step-limited function from statement fragments.

    Host-side of A2's fragment contract (single statement per fragment,
    whole sliced progress + whole merged report, rank-space ids throughout:
    no narrowing, no remap — measured 30/31 on the integrated tree).
    Wrapper + parameter decls + per-statement fragment bodies + (void)
    casts for carried bindings + trailing closing brace. The epilogue
    (pep_leave/return) comes from the trailing return fragment itself,
    exactly as the unit emitter produces it. Fail-closed: non-emitting
    fragments, non-Int/Bool/SourceBytes types, and a missing trailing
    return all raise with the exact position.
    """
    nodes = fields_map(sl)["nodes"]["value"]
    fn_nodes = [n for n in nodes
                if nval(n, "kind") == "function"
                and str(nval(n, "parentId")) == "-1"]
    if len(fn_nodes) != 1:
        raise ValueError(
            "Pep C23 fragment assembly needs a single-function slice")
    fn_id = int(nval(fn_nodes[0], "id"))
    # statement positions are rank ids in source order (remap preserves it)
    order = sorted(int(nval(n, "id")) for n in nodes
                   if str(nval(n, "parentId")) == str(fn_id)
                   and str(nval(n, "role")) == "statement")
    if not order:
        raise ValueError(
            f"Pep C23 fragment assembly found no statements for {name}")
    # trailing statement must be the return (its fragment carries the epilogue)
    last_kind = next(nval(n, "kind") for n in nodes
                     if int(nval(n, "id")) == order[-1])
    if last_kind != "return":
        raise ValueError(
            f"Pep C23 fragment assembly needs a trailing return in {name}")
    # parameter declarations: sliced node ids (the emitter's pep_arg_<id>),
    # C types from the signature, matched by source-order index
    param_nodes = sorted(int(nval(n, "id")) for n in nodes
                         if nval(n, "kind") == "parameter"
                         and str(nval(n, "parentId")) == str(fn_id))
    params = sorted(sig_entry, key=lambda p: int(p["index"]))
    if len(params) != len(param_nodes):
        raise ValueError(
            f"Pep C23 fragment assembly: {len(params)} signature params "
            f"vs {len(param_nodes)} parameter nodes in {name}")
    pdecls = []
    for p, nid in zip(params, param_nodes):
        ctype = _C_TYPE_BY_NAME.get(p["type"])
        if ctype is None:
            raise ValueError(
                f"Pep C23 fragment assembly: unsupported param type "
                f"{p['type']} in {name}")
        pdecls.append((nid, ctype))
    rep_fields = fields_map(rep)
    carried = [(str(_fval(b, "name")), str(int(_fval(b, "syntaxId"))))
               for b in rep_fields["bindings"]["value"]]
    out = []
    out.append("int64_t pep_fn_%s(%s) {\n" % (
        name, ", ".join("%s pep_arg_%s" % (t, i) for i, t in pdecls)))
    out.append("  pep_enter();\n")
    for i, _ in pdecls:
        out.append(f"  (void)pep_arg_{i};\n")
    declared = {str(int(nval(n, "id"))) for n in nodes}
    for pos in range(len(order)):
        status, diag, parts, _ = emit_fragment(
            session, sem, sl, rep, 0, pos, 1)
        if status != "emitted":
            got = diag if isinstance(diag, str) else diag.get("value", diag)
            raise ValueError(
                f"Pep C23 fragment {pos} of {name} refused: {got}")
        out.extend(parts if isinstance(parts, list) else [parts])
    for _bname, _bsid in carried:
        if _bsid not in declared:
            raise ValueError(
                f"Pep C23 fragment assembly: carried binding {_bname} "
                f"has no declaration in the emitted slice of {name}")
        out.append(f"  (void)pep_local_{_bsid};\n")
    out.append("}\n")
    return "".join(str(x) for x in out)


def _top_level_declarations(nodes):
    return [n for n in nodes
            if str(nval(n, "parentId")) == "-1" and nval(n, "kind") != "function"]


def build_c23(session, sem, parsed, tool_revision, tool_doc, target, sample,
              measurements):
    """Full sectional build: check every function, emit sections, assemble.

    Fail-closed: first invalid slice or first refused section raises
    ValueError with the exact diagnostic (same channel as the one-shot path).
    v1 scope: declaration-free programs (records/unions section separately);
    programs with top-level non-function nodes refuse with a clear message.
    Returns the assembled C text.
    """
    import pep_c23
    from tests.test_chunk_typed import host_builtins
    register_sectional_tools(session, tool_doc, tool_revision, sample, pep_c23)
    nodes = fields_map(parsed)["nodes"]["value"]
    decls = _top_level_declarations(nodes)
    if decls:
        raise ValueError(
            "Pep C23 sectional build does not yet cover top-level declarations; "
            f"found {len(decls)} declaration node(s)")
    host = host_builtins(target["document"], target["revision"])
    checked = check_program(session, sem, parsed, tool_revision, target, host)
    if checked["failures"]:
        name, pos, codes = checked["failures"][0]
        raise ValueError(
            f"Pep C23 sectional check failed in {name}: {codes}")
    order, slices, reports = (checked["order"], checked["slices"],
                              checked["reports"])
    if "main" not in slices:
        raise ValueError(
            "Pep C23 emission requires a top-level function named main")
    # Header comes from the first slice in source order so the assembled
    # prototype block keeps source order (matching one-shot output); the
    # remaining slices contribute their prototypes explicitly.
    first = order[0]
    status, diag, header, _ = emit_section(
        session, sem, slices[first], reports[first], "header")
    if status != "emitted":
        raise ValueError(diag or "Pep C23 header section refused the program")
    rebuilt = list(header)
    for name in order[1:]:
        status, diag, protos, _ = emit_section(
            session, sem, slices[name], reports[name], "prototypes")
        if status != "emitted":
            raise ValueError(diag or f"Pep C23 prototypes refused {name}")
        rebuilt.extend(protos)
    for name in order:
        status, diag, parts, _ = emit_unit(
            session, sem, slices[name], reports[name], 0)
        if status != "emitted":
            code = diag if isinstance(diag, str) else diag.get("value", diag)
            if "STEP_LIMIT" not in str(code):
                raise ValueError(
                    diag or f"Pep C23 function unit refused {name}")
            # A3-151 fallback: whole-unit budget exceeded; assemble the
            # function statement-by-statement through the fragment entry.
            # (No narrowing: measured 30/31 on full sliced progress.)
            sig = next((s for s in checked["sigs"]
                          if s.get("name") == name), None)
            if sig is None:
                raise ValueError(
                    f"Pep C23 fragment assembly found no signature for {name}")
            sig_params = [{"index": pi, "type": tname}
                          for (tname, _shp, pi) in sig.get("ptypes", [])]
            parts = [build_fragmented_function(
                session, sem, slices[name], reports[name], name,
                sig_params)]
            stats_entry = checked["stats"].get(name, {}) or {}
            stats_entry["mode"] = (str(stats_entry.get("mode", ""))
                                     + "+fragmented")
            checked["stats"][name] = stats_entry
        rebuilt.extend(parts if isinstance(parts, list) else [parts])
    status, diag, epilogue, _ = emit_section(
        session, sem, slices["main"], reports["main"], "main")
    if status != "emitted":
        raise ValueError(diag or "Pep C23 main section refused the program")
    rebuilt.extend(epilogue)
    text = "".join(rebuilt)
    if "pep_arena" in text and '#include "pep_arena.h"' not in text:
        raise ValueError(
            "Pep C23 sectional build hit mixed arena requirements across slices")
    measurements["sectional_order"] = order
    measurements["sectional_stats"] = checked["stats"]
    return text
