"""Host-side per-function chunker: parse once, check each function in its
own budget-sized analyze_chunk invocation with external signatures."""
import copy
from collections import defaultdict

FIXED = {("binary", "left"): 0, ("binary", "right"): 1, ("unary", "operand"): 0,
         ("if_expression", "condition"): 0, ("if_expression", "then"): 1, ("if_expression", "else"): 2,
         ("match", "value"): 0, ("match_arm", "pattern"): 0, ("match_arm", "result"): 1,
         ("record_field", "value"): 0, ("type_list", "element_type"): 0,
         ("parameter", "type"): 0, ("field_declaration", "type"): 0,
         ("function", "return_type"): 0, ("assignment", "value"): 0,
         ("return", "value"): 0, ("expression_statement", "value"): 0,
         ("for_in", "iterable"): 0, ("while", "condition"): 0,
         ("let", "annotation"): 0, ("let", "value"): 0, ("var", "annotation"): 0, ("var", "value"): 0}

def T(typ, val):
    return {"type": typ, "value": str(val) if typ == "Int" else val}

def fields_map(rec):
    return {f["name"]: f["value"] for f in rec.get("fields", [])}

def nval(node, key):
    return fields_map(node).get(key, {}).get("value")

def setnval(node, key, v):
    for f in node["fields"]:
        if f["name"] == key:
            f["value"]["value"] = v
            return

def children_of(nodes, pid):
    return [n for n in nodes if str(nval(n, "parentId")) == str(pid)]

def sigs_from_tool(result):
    # Parse List[ResolvedSignature] tool output into plain dicts.
    # Transport parsing only; all types were constructed by the checker.
    # Note: scalar fields are {type, value}; record fields are {type, fields}.
    out = []
    items = result.get("value", []) if isinstance(result, dict) else []
    for i, s in enumerate(items):
        f = fields_map(s)
        params = []
        plist = f.get("params", {})
        plist = plist.get("value", []) if isinstance(plist, dict) else []
        for p in plist:
            pf = fields_map(p)
            idx = pf.get("index", {}).get("value", "0")
            tnm = pf.get("typeName", {}).get("value", "")
            shp = fields_map(pf.get("shape", {}))
            sk = shp.get("kind", {}).get("value", "")
            sn = shp.get("name", {}).get("value", "")
            sd = shp.get("listDepth", {}).get("value", "0")
            params.append((tnm, (sk, sn, int(sd or 0)), int(idx or 0)))
        rsh = fields_map(f.get("returnShape", {}))
        rk = rsh.get("kind", {}).get("value", "")
        rn = rsh.get("name", {}).get("value", "")
        rd = rsh.get("listDepth", {}).get("value", "0")
        out.append({"name": f.get("functionName", {}).get("value", ""),
                    "arity": len(params),
                    "rtype": f.get("returnType", {}).get("value", ""),
                    "rshape": (rk, rn, int(rd or 0)),
                    "semid": 9000 + i, "synid": 1000000000 + i, "ptypes": params,
                    "id": f.get("functionId", {}).get("value", "0"),
                    "start": "0", "end": "0"})
    return out

def decl_closure(nodes, fn_sub, sigs_by_name, decl_name_to_id, v2u):
    # Purely textual over-approximation (no type reconstruction): a decl
    # is included if its name appears anywhere it could be referenced.
    # Over-inclusion is bounded waste; under-inclusion fails closed.
    texts = {nval(x, "text") for x in fn_sub if nval(x, "text")}
    refs = set(t for t in texts if t in decl_name_to_id)
    for t in texts:
        if t in v2u:
            refs.add("__union:" + v2u[t])
    for x in fn_sub:
        if nval(x, "kind") == "call" and nval(x, "text") in sigs_by_name:
            rt = sigs_by_name[nval(x, "text")].get("rtype", "") or ""
            for d in decl_name_to_id:
                if d and d in rt:
                    refs.add(d)
    # Field-access bases resolved precisely via a local binding map.
    # Names come from annotation type_named texts (structural) or call
    # rtype shapes from checker sigs (structured). No reconstruction.
    bmap = {}
    for x in fn_sub:
        if nval(x, "kind") == "parameter":
            tch = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "type"]
            for t in tch:
                for tn in [t] + [c for c in children_of(nodes, nval(t, "id"))]:
                    if nval(tn, "kind") in ("type_named", "type_scalar"):
                        bmap[nval(x, "text")] = nval(tn, "text")
        if nval(x, "kind") in ("let", "var"):
            nm = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "name"]
            an = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "annotation"]
            vl = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "value"]
            if nm:
                named = nval(nm[0], "text")
                for a in an:
                    for tn in [a] + [c for c in children_of(nodes, nval(a, "id"))]:
                        if nval(tn, "kind") in ("type_named", "type_scalar"):
                            bmap[named] = nval(tn, "text")
                if named not in bmap:
                    for v in vl:
                        if nval(v, "kind") == "call" and nval(v, "text") in sigs_by_name:
                            rs = sigs_by_name[nval(v, "text")].get("rshape", ("", "", 0))
                            if rs[0] == "nominal" and rs[1]:
                                bmap[named] = rs[1]
    for x in fn_sub:
        if nval(x, "kind") == "field_access":
            v = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "value"]
            if v and nval(v[0], "kind") == "name" and nval(v[0], "text") in bmap:
                refs.add(bmap[nval(v[0], "text")])
            if v and nval(v[0], "kind") == "call" and nval(v[0], "text") in sigs_by_name:
                rs = sigs_by_name[nval(v[0], "text")].get("rshape", ("", "", 0))
                if rs[0] == "nominal" and rs[1]:
                    refs.add(rs[1])
    out = []
    seen = {str(nval(y, "id")) for y in fn_sub}
    for dname, did in decl_name_to_id.items():
        if dname in refs or ("__union:" + did) in refs:
            for sn in slice_subtree(nodes, did):
                sid = str(nval(sn, "id"))
                if sid not in seen:
                    seen.add(sid)
                    out.append(sn)
    return out

def header_subtree(nodes, by_id, fn_id):
    # Function header only (no statement-rooted bodies): tiny, always fits.
    def in_body(n):
        p = str(nval(n, "parentId"))
        while p != "-1":
            pn = by_id.get(p)
            if pn is None:
                return False
            if nval(pn, "role") == "statement":
                return True
            p = str(nval(pn, "parentId"))
        return False
    keep = set()
    stack = [str(fn_id)]
    while stack:
        cur = stack.pop()
        if cur in keep:
            continue
        keep.add(cur)
        for c in nodes:
            if str(nval(c, "parentId")) == cur and nval(c, "role") != "statement" and not in_body(c):
                stack.append(str(nval(c, "id")))
    return [copy.deepcopy(n) for n in nodes if str(nval(n, "id")) in keep]

def fetch_all_sigs(session, parsed, tool_revision, sem, tool_name="pep-c23-checker-sigs"):
    # Authoritative signatures via per-function header chunks (each tiny).
    # No host-side type reconstruction; transport only.
    nodes = fields_map(parsed)["nodes"]["value"]
    by_id = {str(nval(n, "id")): n for n in nodes}
    fns = [n for n in nodes if nval(n, "kind") == "function" and str(nval(n, "parentId")) == "-1"]
    allsigs = []
    for fn in fns:
        original_id = str(nval(fn, "id"))
        sub = header_subtree(nodes, by_id, nval(fn, "id"))
        chunk = remap_chunk(sub)
        hp = {"type": "ParserProgress", "fields": [
            {"name": k, "value": ({"type": "List[FlatAstNode]", "value": chunk} if k == "nodes" else fields_map(parsed)[k])}
            for k in [f["name"] for f in parsed["fields"]]]}
        r = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                          "tool": tool_name, "arguments": [hp], "semanticTarget": sem})
        if r.get("outcome") != "ok":
            raise RuntimeError(f"signatures chunk failed: {r.get('error', {}).get('code')}")
        chunk_sigs = sigs_from_tool(r["result"])
        if len(chunk_sigs) != 1:
            raise RuntimeError("a header chunk must certify exactly one function signature")
        # Two id spaces, kept separate on purpose:
        #   id/synid  - the chunk-local identity the checker keys external
        #               signatures by (synthetic, never a document id);
        #   node      - the original document node id the host cut this header
        #               chunk from, which is the only identity the checked-chunk
        #               contract can tie to this revision.
        # Using a document id as the checker-side key collides with the
        # remapped ids of a body chunk and silently loses cross-chunk type
        # checking (measured).
        chunk_sigs[0]["node"] = original_id
        allsigs.extend(chunk_sigs)
    return allsigs

def variant_to_union(nodes):
    m = {}
    for n in nodes:
        if nval(n, "kind") == "variant_declaration":
            m[nval(n, "text")] = str(nval(n, "parentId"))
    return m

def resolved_sig_value(sig):
    pfacts = []
    for tname, (sk, sn, sd), pi in sig.get("ptypes", []):
        pfacts.append({"type": "ParamTypeFact", "fields": [
            {"name": "index", "value": T("Int", pi)},
            {"name": "typeName", "value": T("Str", tname)},
            {"name": "shape", "value": {"type": "PepTypeShape", "fields": [
                {"name": "kind", "value": T("Str", sk)},
                {"name": "name", "value": T("Str", sn)},
                {"name": "listDepth", "value": T("Int", sd)}]}}]})
    rsk, rsn, rsd = sig.get("rshape", ("", "", 0))
    return {"type": "ResolvedSignature", "fields": [
        {"name": "functionId", "value": T("Int", sig["synid"])},
        {"name": "functionName", "value": T("Str", sig["name"])},
        {"name": "params", "value": {"type": "List[ParamTypeFact]", "value": pfacts}},
        {"name": "returnType", "value": T("Str", sig.get("rtype", ""))},
        {"name": "returnShape", "value": {"type": "PepTypeShape", "fields": [
            {"name": "kind", "value": T("Str", rsk)},
            {"name": "name", "value": T("Str", rsn)},
            {"name": "listDepth", "value": T("Int", rsd)}]}}]}

def checked_fn_value(sig):
    sk, sn, sd = sig["rshape"]
    return {"type": "CheckedFunction", "fields": [
        {"name": "semanticId", "value": T("Int", sig["semid"])},
        {"name": "syntaxId", "value": T("Int", sig["synid"])},
        {"name": "name", "value": T("Str", sig["name"])},
        {"name": "arity", "value": T("Int", sig["arity"])},
        {"name": "returnType", "value": T("Str", sig["rtype"])},
        {"name": "returnShape", "value": {"type": "PepTypeShape", "fields": [
            {"name": "kind", "value": T("Str", sk)},
            {"name": "name", "value": T("Str", sn)},
            {"name": "listDepth", "value": T("Int", sd)}]}},
        {"name": "startByte", "value": T("Int", sig["start"])},
        {"name": "endByte", "value": T("Int", sig["end"])}]}

def slice_subtree(nodes, root_id):
    keep = {str(root_id)}
    changed = True
    while changed:
        changed = False
        for n in nodes:
            if str(nval(n, "parentId")) in keep and str(nval(n, "id")) not in keep:
                keep.add(str(nval(n, "id"))); changed = True
    return [copy.deepcopy(n) for n in nodes if str(nval(n, "id")) in keep]

def compact_node(node):
    # Compact projection for emitter-bound chunks (per A2 field audit):
    # drop exactly stringParts, line, column; keep the other 10 fields.
    # Literal text is recovered from source_bytes() + byte spans.
    return {"type": node.get("type", "FlatAstNode"),
            "fields": [f for f in node.get("fields", [])
                       if f.get("name") not in ("stringParts", "line", "column")]}

def remap_chunk(sub):
    sub.sort(key=lambda n: int(nval(n, "id")))
    remap = {str(nval(n, "id")): str(i) for i, n in enumerate(sub)}
    for n in sub:
        setnval(n, "id", remap[str(nval(n, "id"))])
        if str(nval(n, "parentId")) != "-1":
            setnval(n, "parentId", remap[str(nval(n, "parentId"))])
    kind_by_id = {str(nval(n, "id")): nval(n, "kind") for n in sub}
    rolecount = defaultdict(int)
    rootcount = 0
    for n in sub:
        p = str(nval(n, "parentId"))
        if p == "-1":
            setnval(n, "childIndex", str(rootcount)); rootcount += 1
        else:
            pk, rl = kind_by_id[p], nval(n, "role")
            if (pk, rl) in FIXED:
                setnval(n, "childIndex", str(FIXED[(pk, rl)]))
            else:
                setnval(n, "childIndex", str(rolecount[(p, rl)])); rolecount[(p, rl)] += 1
    return sub
