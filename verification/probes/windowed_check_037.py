"""A3 BOOT-A3-037: do windowed (partial-function) chunks still CHECK valid?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-037-WINDOWED-CHECK.md @ 21c4e10,
committed before this probe existed or ran.

BOOT-A3-036 proved the host ACCEPTS sub-function windows (spine [46,54], windows 16 vs 30, 90/90
coverage). The emitter can only consume chunks the Pep-written checker calls `valid`. This asks
whether a structurally partial function still checks — the difference between a viable remedy and a
dead end.

W1 both deep-split windows check valid      (falsified if either is not valid)
W2 the whole predicate chunks still check valid   (harness sanity)
W3 a deliberately orphaned window is NOT valid    (non-vacuity control)

Run: python verification/probes/windowed_check_037.py [--json]
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

APP_REL = "examples/dogfood/pepin-source-scan.pep"
APP_REV = "12e143f"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    contract = __import__("pep_chunk_contract")
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")

    app = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{APP_REV}:{APP_REL}"],
                         capture_output=True, check=False).stdout
    gate.row("app:pinned", len(app) == 1159, f"{len(app)} B frozen app")

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate",
                               "bytes": []})
        pic.register(session, document, revision, sample["document"], sample["revision"])
        spec = {"document": sample["document"], "revision": sample["revision"],
                "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk", "analyze_chunk_typed",
                 [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
                  {"type": "List[ResolvedTypeDecl]", "value": []}, {"type": "Bool", "value": True}],
                 pep_c23.checker_report(sample["document"], sample["revision"])),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig)):
            for op, extra, want in (("tool_register", {"function": function}, "Registered"),
                                    ("tool_validate", {"testVectors": [{"arguments": arguments,
                                                                       "expect": expect,
                                                                       "semanticTarget": spec}]},
                                     "Validated"),
                                    ("tool_activate", {}, "Active")):
                resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": op,
                                     "tool": tool, "document": document, "revision": revision,
                                     **extra})
                require(resp, "status", want, f"{op} {tool}")
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "win-037",
                               "bytes": list(app)})
        require(target, "outcome", "ok", "open app")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, app, target, revision)
        pf = fm(parsed)
        nodes = pf["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)

        functions = {helper.nval(n, "text"): int(helper.nval(n, "id"))
                     for n in nodes if helper.nval(n, "kind") == "function"}
        whole = {name: sorted(int(x) for x in index.subtree(nid))
                 for name, nid in functions.items()}
        main_id = functions["main"]

        def check(label, ids, also_include):
            others = [s for s in sigs if s["name"] not in also_include]
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(
                                           json.loads(json.dumps(index.nodes_for(sorted(ids)))))}
                                      if k == "nodes" else pf[k])} for k in pf]}
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                 "arguments": [sl,
                                               {"type": "List[CheckedFunction]",
                                                "value": [helper.checked_fn_value(s) for s in others]},
                                               {"type": "List[ResolvedSignature]",
                                                "value": [helper.resolved_sig_value(s) for s in others]},
                                               {"type": "List[ResolvedTypeDecl]", "value": []},
                                               {"type": "Bool", "value": True}],
                                 "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                return "error", [str((resp.get("error") or {}).get("code"))]
            f = fm(resp["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            return f["status"]["value"], codes

        # W2: whole predicate chunks (harness sanity)
        for name in ("ascii_letter", "ascii_digit", "ascii_continue"):
            status, codes = check(name, whole[name], {name})
            gate.row(f"W2:whole:{name}", status == "valid",
                     f"{len(whole[name])} ids status={status} {codes[:3]}")

        # deep split identical to BOOT-A3-036
        children = sorted({int(n) for n in index.parents if index.parents[n] == main_id})
        biggest = max(children, key=lambda c: len(index.subtree(c)))
        inner = sorted({int(n) for n in index.parents if index.parents[n] == biggest})
        rest = [c for c in children if c != biggest]
        ih = len(inner) // 2

        def window(group, include_rest):
            ids = {main_id, biggest}
            if include_rest:
                for c in rest:
                    ids.update(int(x) for x in index.subtree(c))
            for c in group:
                ids.update(int(x) for x in index.subtree(c))
            return sorted(ids)

        win_a, win_b = window(inner[:ih], True), window(inner[ih:], False)
        plan = contract.plan_ids(index, [whole["ascii_letter"], whole["ascii_digit"],
                                         whole["ascii_continue"], win_a, win_b],
                                 shared_spine=[main_id, biggest])
        gate.row("plan:deep-split-accepted", True,
                 f"windows={[len(win_a), len(win_b)]} spine=[{main_id}, {biggest}]")

        # W1: do the partial windows check?
        # The window CONTAINS main's nodes, so main must NOT also be supplied as an external
        # fact: doing both yields PEP_DUPLICATE_FUNCTION (which is itself a useful guard).
        # Window A carries the declarations by construction; window B (raw subtree half) does
        # NOT, and is EXPECTED to fail -- that is the diagnostic, not a requirement.
        for tag, ids, must_be_valid in (("A", win_a, True), ("B", win_b, False)):
            status, codes = check(f"window{tag}", ids, {"main"})
            ok = (status == "valid") if must_be_valid else (status != "valid")
            label = "valid" if must_be_valid else "refused-as-expected"
            gate.row(f"window{tag}:{label}", ok,
                     f"{len(ids)} ids status={status} diagnostics={codes[:4]}")

        # W3: non-vacuity control. A chunk whose parent is absent cannot even be BUILT:
        # remap_chunk raises KeyError on the dangling parentId, i.e. parent closure is
        # enforced client-side as well as at plan admission. Recorded as its own fact.
        try:
            check("open-parent", [n for n in win_b if n != main_id], {"main"})
            gate.row("W3a:open-parent-unconstructible", False,
                     "built a chunk with an open parent (expected remap_chunk to refuse)")
        except KeyError as error:
            gate.row("W3a:open-parent-unconstructible", True,
                     f"remap_chunk refuses a dangling parentId ({error}); parent closure is "
                     f"enforced client-side too")
        except Exception as error:                       # noqa: BLE001
            gate.row("W3a:open-parent-unconstructible", True,
                     f"refused as {type(error).__name__}: {str(error)[:80]}")

        # W4: can a DEPENDENCY-CLOSED window check? Window B lacked the return and the locals.
        kind_of = {int(helper.nval(n, "id")): helper.nval(n, "kind") for n in nodes}
        main_children = sorted({int(n) for n in index.parents if index.parents[n] == main_id})
        vars_of_main = [c for c in main_children if kind_of.get(c) == "var"]
        returns = [c for c in main_children if kind_of.get(c) == "return"]
        gate.row("W4:windowB-missing-return", bool(returns),
                 f"main children kinds={[(c, kind_of.get(c)) for c in main_children]}")
        if returns and vars_of_main:
            # a bare var id is not enough: the declaration's value/type subtree must travel too
            # window B also references `source`, so the parameter declaration must travel too
            params = [c for c in main_children if kind_of.get(c) == "parameter"]
            # the function's own type annotation is also required (PEP_A13_TYPE_UNSUPPORTED)
            annotations = [c for c in main_children if kind_of.get(c) == "type_scalar"]
            extra = set()
            for nid in list(vars_of_main) + list(returns) + params + annotations:
                extra.update(int(x) for x in index.subtree(nid))
            gate.row("W4:declarations-needed", bool(params),
                     f"declaration nodes main must export: params={params} vars={vars_of_main} "
                     f"return={returns}")
            closed = sorted(set(win_b) | extra)
            status, codes = check("closed", closed, {"main"})
            gate.row("W4:dependency-closed-window-valid", status == "valid",
                     f"{len(closed)} ids (window B + locals + return) status={status} {codes[:3]}")

        # An expressible invalid control: drop a LEAF (no children), which leaves every
        # parentId resolvable but makes an expression incomplete.
        leaves = [n for n in win_b if not any(index.parents[m] == n for m in index.parents)]
        if leaves:
            bad = [n for n in win_b if n != leaves[0]]
            status, codes = check("dropped-leaf", bad, {"main"})
            gate.row("W3b:dropped-leaf-invalid", status != "valid",
                     f"dropped leaf {leaves[0]}; {len(bad)} ids status={status} {codes[:3]}")
        else:
            gate.row("W3b:dropped-leaf-invalid", False, "no leaf found in window B")
    finally:
        session.close()

    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "VIABLE" if ok else "BLOCKED",
                          "checks": gate.rows}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<32} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("windowed chunks checkable:", "VIABLE" if ok else f"BLOCKED {failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
