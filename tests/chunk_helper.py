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

def type_string(nodes, tid):
    tns = [n for n in nodes if str(nval(n, "id")) == str(tid)]
    if not tns:
        return ""
    tn = tns[0]
    k = nval(tn, "kind")
    if k in ("type_scalar", "type_named"):
        return nval(tn, "text")
    if k == "type_list":
        for c in children_of(nodes, tid):
            if nval(c, "role") == "element_type":
                return "List[" + type_string(nodes, nval(c, "id")) + "]"
    return ""

def type_shape(nodes, tid):
    tns = [n for n in nodes if str(nval(n, "id")) == str(tid)]
    if not tns:
        return ("", "", 0)
    tn = tns[0]
    k = nval(tn, "kind")
    if k == "type_scalar":
        return ("builtin", nval(tn, "text"), 0)
    if k == "type_named":
        return ("nominal", nval(tn, "text"), 0)
    if k == "type_list":
        for c in children_of(nodes, tid):
            if nval(c, "role") == "element_type":
                sk, sn, sd = type_shape(nodes, nval(c, "id"))
                return (sk, sn, sd + 1)
    return ("", "", 0)

def decl_closure(nodes, fn_sub, sigs_by_name, decl_name_to_id, v2u):
    refs = set()
    # 1. all nominal names inside type annotations in the function
    def collect_type_names(tid):
        tns = [n for n in nodes if str(nval(n, "id")) == str(tid)]
        if not tns:
            return
        tn = tns[0]
        k = nval(tn, "kind")
        if k == "type_named":
            refs.add(nval(tn, "text"))
        for c in children_of(nodes, tid):
            collect_type_names(nval(c, "id"))
    fn_ids = {str(nval(x, "id")) for x in fn_sub}
    for x in fn_sub:
        if nval(x, "kind") in ("type_scalar", "type_named", "type_list"):
            collect_type_names(nval(x, "id"))
        if nval(x, "kind") == "record" and nval(x, "text"):
            refs.add(nval(x, "text"))
        if nval(x, "kind") in ("record", "call", "constructor_pattern") and nval(x, "text") in v2u:
            refs.add("__union:" + v2u[nval(x, "text")])
    # 2. call return types via signatures (local + external)
    for x in fn_sub:
        if nval(x, "kind") == "call" and nval(x, "text") in sigs_by_name:
            rt = sigs_by_name[nval(x, "text")]["rtype"]
            if rt and rt not in ("Int", "Bool", "Str", "Unit", "SourceBytes") and not rt.startswith("List["):
                refs.add(rt)
            elif rt.startswith("List[") and rt.endswith("]"):
                inner = rt[5:-1]
                if inner and inner not in ("Int", "Bool", "Str", "Unit", "SourceBytes"):
                    refs.add(inner)
    # 3. field-access base types via local binding map (params + annotated lets)
    bmap = {}
    for x in fn_sub:
        if nval(x, "kind") == "parameter":
            tch = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "type"]
            if tch:
                tn = type_string(nodes, nval(tch[0], "id"))
                if tn:
                    bmap[nval(x, "text")] = tn
        if nval(x, "kind") in ("let", "var"):
            nm = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "name"]
            an = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "annotation"]
            if nm and an:
                tn = type_string(nodes, nval(an[0], "id"))
                if tn:
                    bmap[nval(nm[0], "text")] = tn
    for x in fn_sub:
        if nval(x, "kind") == "field_access":
            v = [c for c in children_of(nodes, nval(x, "id")) if nval(c, "role") == "value"]
            if v and nval(v[0], "kind") == "name" and nval(v[0], "text") in bmap:
                bt = bmap[nval(v[0], "text")]
                if bt and not bt.startswith("List["):
                    refs.add(bt)
                elif bt.startswith("List[") and bt.endswith("]"):
                    refs.add(bt[5:-1])
            if v and nval(v[0], "kind") == "call" and nval(v[0], "text") in sigs_by_name:
                rt = sigs_by_name[nval(v[0], "text")]["rtype"]
                if rt and not rt.startswith("List[") and rt not in ("Int", "Bool", "Str", "Unit", "SourceBytes"):
                    refs.add(rt)
    # 4. materialise referenced decl subtrees
    out = []
    for dname, did in decl_name_to_id.items():
        if dname in refs or ("__union:" + did) in refs:
            for sn in slice_subtree(nodes, did):
                if str(nval(sn, "id")) not in fn_ids and \
                        all(str(nval(y, "id")) != str(nval(sn, "id")) for y in out):
                    out.append(sn)
    return out

def variant_to_union(nodes):
    m = {}
    for n in nodes:
        if nval(n, "kind") == "variant_declaration":
            m[nval(n, "text")] = str(nval(n, "parentId"))
    return m

def extract_sigs(nodes):
    sigs = []
    for i, n in enumerate([x for x in nodes if nval(x, "kind") == "function" and str(nval(x, "parentId")) == "-1"]):
        fid = nval(n, "id")
        kids = children_of(nodes, fid)
        params = [c for c in kids if nval(c, "kind") == "parameter"]
        ptypes = []
        for pi, p in enumerate(params):
            tch = [c for c in children_of(nodes, nval(p, "id")) if nval(c, "role") == "type"]
            if tch:
                ptypes.append((type_string(nodes, nval(tch[0], "id")) or "",
                               type_shape(nodes, nval(tch[0], "id")), pi))
            else:
                ptypes.append(("", ("", "", 0), pi))
        ret = [c for c in kids if nval(c, "role") == "return_type"]
        rtype, rshape = "Unit", ("builtin", "Unit", 0)
        if ret:
            rtype = type_string(nodes, nval(ret[0], "id")) or "Unit"
            rshape = type_shape(nodes, nval(ret[0], "id"))
            if rshape[0] == "":
                rshape = ("builtin", "Unit", 0)
        sigs.append({"name": nval(n, "text"), "arity": len(params),
                     "rtype": rtype, "rshape": rshape, "semid": 9000 + i,
                     "synid": 1000000000 + i, "ptypes": ptypes,
                     "start": nval(n, "startByte"), "end": nval(n, "endByte"),
                     "id": fid})
    return sigs

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
    return {"type": "ResolvedSignature", "fields": [
        {"name": "functionId", "value": T("Int", sig["synid"])},
        {"name": "functionName", "value": T("Str", sig["name"])},
        {"name": "params", "value": {"type": "List[ParamTypeFact]", "value": pfacts}}]}

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
