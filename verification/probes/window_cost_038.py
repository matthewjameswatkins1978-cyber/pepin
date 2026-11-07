"""A3 BOOT-A3-038: does a dependency-closed window actually EMIT inside the 100k budget?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-038-WINDOW-COST.md @ 658a9a9,
committed before this probe existed or ran.

COST PROBE ONLY. A window is a semantically incomplete function (half a loop body): an emitted unit
would compute the wrong answer. Nothing here is compiled or run for correctness, and no window is
presented as an application. The only outputs are: did `pep-c23-unit` emit, and how many interpreter
steps did it cost.

Decision it informs: whether A2 should build a windowed emitter at all, or spend the time on cheaper
lowering instead (BOOT-A3-033's quadratic node term).

Run: python verification/probes/window_cost_038.py [--json]
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
BUDGET = 100_000


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
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
                ("pep-c23-section", "emit_c23_section",
                 [empty_pp, pep_c23.checker_report(sample["document"], sample["revision"]),
                  typed("Str", "header")],
                 pep_c23.typed_record("unsupported", (),
                                      "Pep C23 emission requires a top-level function named main"))):
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

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "wincost-038",
                               "bytes": list(app)})
        require(target, "outcome", "ok", "open app")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, app, target, revision)
        pf = fm(parsed)
        nodes = pf["nodes"]["value"]
        index = contract.DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)

        kind_of = {int(helper.nval(n, "id")): helper.nval(n, "kind") for n in nodes}
        functions = {helper.nval(n, "text"): int(helper.nval(n, "id"))
                     for n in nodes if helper.nval(n, "kind") == "function"}
        main_id = functions["main"]
        whole_main = sorted(int(x) for x in index.subtree(main_id))

        def slice_of(ids):
            return {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(
                                           json.loads(json.dumps(index.nodes_for(sorted(ids)))))}
                                      if k == "nodes" else pf[k])} for k in pf]}

        def check_and_emit(label, ids):
            others = [s for s in sigs if s["name"] != "main"]
            sl = slice_of(ids)
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
                return "check-error", None, None, str((resp.get("error") or {}).get("code"))
            f = fm(resp["result"])
            if f["status"]["value"] != "valid":
                codes = [fm(x).get("code", {}).get("value")
                         for x in (f.get("diagnostics", {}).get("value") or [])]
                return "check-invalid", None, codes, None
            emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-unit",
                                    "arguments": [sl, resp["result"], typed("Int", 0)],
                                    "semanticTarget": sem})
            metrics = session.send({"schemaVersion": 3, "op": "metrics"})
            steps = (metrics.get("metrics") or {}).get("last_execute_steps")
            if emitted.get("outcome") != "ok":
                return "refused", steps, [(emitted.get("error") or {}).get("code")], \
                    (emitted.get("error") or {}).get("message", "")[:100]
            ef = fm(emitted["result"])
            if ef["status"]["value"] != "emitted":
                return "unsupported", steps, None, ef["diagnostic"]["value"][:140]
            return "emitted", steps, None, f"{sum(len(p['value']) for p in ef['sourceParts']['value'])} C bytes"

        # --- windows, constructed exactly as BOOT-A3-037's final form ----------
        children = sorted({int(n) for n in index.parents if index.parents[n] == main_id})
        biggest = max(children, key=lambda c: len(index.subtree(c)))
        inner = sorted({int(n) for n in index.parents if index.parents[n] == biggest})
        rest = [c for c in children if c != biggest]
        ih = len(inner) // 2

        # ROLE-AWARE split: a while needs its CONDITION and a non-empty assignment body in
        # every window, so the condition and the sole `assignment` body statement are shared
        # spine, and only the remaining body statement (the big `if`) is separable.
        role_of = {int(helper.nval(n, "id")): helper.nval(n, "role") for n in nodes}
        cond = [c for c in inner if role_of.get(c) == "condition"]
        body = [c for c in inner if role_of.get(c) == "body"]
        assigns = [c for c in body if kind_of.get(c) == "assignment"]
        big_stmt = [c for c in body if kind_of.get(c) != "assignment"]
        gate.row("roles:while-shape", bool(cond) and bool(assigns),
                 f"while children: condition={cond} body={[(c, kind_of.get(c)) for c in body]}")

        decl_kinds = {"var", "parameter", "type_scalar", "return"}
        decls = [c for c in children if kind_of.get(c) in decl_kinds]
        # every shared node must travel with its FULL subtree: a bare `unary` condition has
        # no operand, and a bare declaration is not a declaration (same lesson as BOOT-A3-037)
        shared = {main_id, biggest}
        for c in list(cond) + list(assigns) + decls:
            shared.update(int(x) for x in index.subtree(c))
        win_shared_only = sorted(shared)
        win_big = sorted(shared | {int(x) for c in big_stmt for x in index.subtree(c)})
        spine = sorted({main_id, biggest} | set(cond) | set(assigns))
        gate.row("rooms:spine", True, f"shared spine for the role-aware split = {spine}")
        win_a, win_b = win_big, win_shared_only

        results = {}
        for label, ids in (("windowA", win_a), ("windowB_closed", win_b),
                           ("whole_main", whole_main)):
            status, steps, codes, detail = check_and_emit(label, ids)
            results[label] = {"ids": len(ids), "status": status, "steps": steps,
                              "codes": codes, "detail": detail}
            gate.row(f"{label}:checks", status != "check-invalid" and status != "check-error",
                     f"{len(ids)} ids status={status} codes={codes}")
    finally:
        session.close()

    wa, wb, wm = results["windowA"], results["windowB_closed"], results["whole_main"]

    # C1: the 39-node closed window emits
    if wb["status"] == "emitted":
        gate.row("C1:closed-window-emits", True, f"emitted at {wb['steps']} steps")
    elif wb["status"] == "refused" and "STEP_LIMIT" in str(wb["codes"]):
        gate.row("C1:closed-window-emits", False,
                 f"REFUSED for budget: {wb['steps']} steps, {wb['codes']}")
    else:
        gate.row("C1:closed-window-emits", True,
                 f"NOT TESTED for the budget question - emitter refused for capability: "
                 f"{wb['status']} {wb['codes']} {wb['detail']}")

    # C2 / C3 calibration
    if wb["status"] == "emitted":
        gate.row("C2:closed-window-in-band", 70_000 <= (wb["steps"] or 0) <= 95_000,
                 f"{wb['steps']} steps (predicted 70,000-95,000)")
    else:
        gate.row("C2:closed-window-in-band", True, f"NOT TESTED ({wb['status']})")
    if wa["status"] == "emitted":
        gate.row("C3:small-window-under-40k", (wa["steps"] or 10**9) < 40_000,
                 f"{wa['steps']} steps at {wa['ids']} ids (predicted < 40,000)")
    else:
        gate.row("C3:small-window-under-40k", True, f"NOT TESTED ({wa['status']})")

    # C4: window costs materially less than the whole main
    if wb["status"] == "emitted" and wm["status"] in ("refused", "emitted"):
        wm_steps = wm["steps"] or BUDGET
        gate.row("C4:window-cheaper-than-whole", (wb["steps"] or 0) < wm_steps,
                 f"window {wb['steps']} vs whole main {wm['steps']} ({wm['status']})")
    else:
        gate.row("C4:window-cheaper-than-whole", True, "NOT TESTED")

    ok = all(r["ok"] for r in gate.rows)
    # An all-pass run in which C1 was never measured is NOT "fits". Three states, not two.
    measured = wb["status"] == "emitted" or (
        wb["status"] == "refused" and "STEP_LIMIT" in str(wb["codes"]))
    if not measured:
        verdict = "NOT DETERMINED (emitter capability refusal precedes the budget question)"
    elif wa["status"] == "refused" and wa["ids"] >= wm["ids"]:
        verdict = (f"NO REDUCTION AVAILABLE: windows DO emit (the {wb['ids']}-id window emitted at "
                   f"{wb['steps']} steps) but the window carrying the expensive statement is "
                   f"{wa['ids']} ids - the whole function - and refuses at the same offset")
    elif wb["status"] == "emitted" and ok:
        verdict = "WINDOW FITS"
    else:
        verdict = "WINDOW DOES NOT FIT"
    if as_json:
        print(json.dumps({"verdict": verdict, "results": results,
                          "checks": gate.rows}, indent=2))
    else:
        print("cost per chunk (COST PROBE ONLY - windows are semantically incomplete)\n")
        print(f"{'chunk':16} {'ids':>4} {'status':12} {'steps':>8}  detail")
        for label in ("windowA", "windowB_closed", "whole_main"):
            r = results[label]
            print(f"{label:16} {r['ids']:>4} {r['status']:12} {str(r['steps']):>8}  "
                  f"{r['codes'] or ''} {r['detail'] or ''}"[:150])
        print()
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<30} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("windowed emission capacity:", verdict)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
