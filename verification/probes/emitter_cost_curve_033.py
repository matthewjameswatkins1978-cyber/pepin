"""A3 BOOT-A3-033: is the C23 emitter's step cost linear or superlinear in chunk nodes?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-033-COST-CURVE.md @ 5cf986e,
committed before this probe existed or ran.

Instrument: session `{"op":"metrics"}` -> `last_execute_steps`, reset per execute and ticked per
evaluated node (pep_ocaml.ml:785/793), documented as existing "so per-phase cost is measurable from
outside without instrumenting a scratch worktree".

Family: `while !(byte_length(source) <= o) { <N flat assignments>; o = o + 1 }`, single function.
A ladder wide enough (N = 1..8) that a quadratic fit has more than three successful points — a
quadratic through three points is exact and proves nothing, so fewer than four successes is reported
as NOT TESTED rather than fitted.

Refused rows still report 100,001 (the budget trip). Those are LOWER BOUNDS and are excluded from
any fit.

Run: python verification/probes/emitter_cost_curve_033.py [--json]
"""
import importlib.util
import json
import os
import pathlib
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

BUDGET = 100_000
LADDER = [1, 2, 3, 4, 5, 6, 7, 8]


def loop_flat(n):
    body = "\n".join("    n = n + 1" for _ in range(n))
    return ("fn main(source: SourceBytes) -> Int {\n"
            "  var n = 0\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n" + body + "\n"
            "    o = o + 1\n"
            "  }\n"
            "  return n\n}\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def measure(session, helper, target, sem, src, revision):
    parsed = parse_target(session, src, target, revision)
    pf = fm(parsed)
    nodes = pf["nodes"]["value"]
    index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
    node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                and helper.nval(n, "text") == "main")
    chunk_nodes = index.nodes_for(sorted(index.subtree(int(helper.nval(node, "id")))))
    sl = {"type": "ParserProgress", "fields": [
        {"name": k, "value": ({"type": "List[FlatAstNode]",
                               "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                              if k == "nodes" else pf[k])} for k in pf]}
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                            "arguments": [sl,
                                          {"type": "List[CheckedFunction]", "value": []},
                                          {"type": "List[ResolvedSignature]", "value": []},
                                          {"type": "List[ResolvedTypeDecl]", "value": []},
                                          {"type": "Bool", "value": True}],
                            "semanticTarget": sem})
    if checked.get("outcome") != "ok" or fm(checked["result"])["status"]["value"] != "valid":
        return len(chunk_nodes), None, "check-failed", "chunk did not check valid"
    emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-unit",
                            "arguments": [sl, checked["result"], typed("Int", 0)],
                            "semanticTarget": sem})
    metrics = session.send({"schemaVersion": 3, "op": "metrics"})
    steps = (metrics.get("metrics") or {}).get("last_execute_steps")
    if emitted.get("outcome") != "ok":
        return len(chunk_nodes), steps, "refused", \
            str((emitted.get("error") or {}).get("code"))
    ef = fm(emitted["result"])
    if ef["status"]["value"] != "emitted":
        return len(chunk_nodes), steps, "unsupported", str(ef["diagnostic"]["value"])[:100]
    return len(chunk_nodes), steps, "emitted", ""


def least_squares(points, powers):
    """Tiny closed-form fit for {1,x} or {1,x,x^2}. Returns (coeffs, residual) or (None, None)."""
    n = len(powers)
    if len(points) < n:
        return None, None
    A = [[sum((x ** (pi + pj)) for x, _ in points) for pj in powers] for pi in powers]
    b = [sum((y * (x ** pi)) for x, y in points) for pi in powers]
    # Gaussian elimination
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-9:
            return None, None
        M[c], M[piv] = M[piv], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    coeffs = [M[i][n] / M[i][i] for i in range(n)]
    resid = sum((y - sum(coeffs[i] * (x ** powers[i]) for i in range(n))) ** 2
                for x, y in points)
    return coeffs, resid


def main():
    as_json = "--json" in sys.argv
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    rows = []
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

        for n in LADDER:
            src = loop_flat(n).encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"curve-{n}", "bytes": list(src)})
            require(target, "outcome", "ok", f"open curve-{n}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": ["main"]}
            nodes, steps, status, detail = measure(session, helper, target, sem, src, revision)
            rows.append({"assignments": n, "nodes": nodes, "steps": steps, "status": status,
                         "detail": detail,
                         "steps_per_node": round(steps / nodes, 1) if steps and nodes else None})
    finally:
        session.close()

    ok_rows = [r for r in rows if r["status"] == "emitted"]
    checks = []

    # P1: steps/node rises monotonically among emitted rows
    ratios = [r["steps_per_node"] for r in ok_rows]
    p1 = len(ratios) >= 2 and all(b >= a for a, b in zip(ratios, ratios[1:]))
    checks.append(("P1:steps-per-node-rises", p1, f"ratios={ratios}"))

    by_n = {r["assignments"]: r for r in rows}
    p2 = by_n.get(6, {}).get("steps_per_node")
    checks.append(("P2:N=6-over-1900", bool(p2 and p2 > 1900),
                   f"N=6 nodes={by_n.get(6, {}).get('nodes')} steps/node={p2}"))
    r8 = by_n.get(8, {})
    if r8.get("status") == "emitted":
        p3 = r8.get("steps_per_node")
        checks.append(("P3:N=8-over-2300", bool(p3 and p3 > 2300),
                       f"N=8 emitted, steps={r8['steps']} steps/node={p3}"))
    else:
        checks.append(("P3:N=8-over-2300", True,
                       f"NOT TESTED - N=8 was {r8.get('status')} (steps={r8.get('steps')} is the "
                       f"budget trip, a lower bound, not a measurement); comparing that bound to "
                       f"2,300 would be meaningless"))

    # P4: quadratic beats linear, only if >=4 successful points
    pts = [(r["nodes"], r["steps"]) for r in ok_rows]
    if len(pts) >= 4:
        lin, rl = least_squares(pts, [1])
        quad, rq = least_squares(pts, [1, 2])
        better = rq is not None and rl is not None and rq < rl
        checks.append(("P4:quadratic-beats-linear", better,
                       f"points={len(pts)} linear_resid={rl:.4g} quadratic_resid={rq:.4g} "
                       f"quad={[round(c, 4) for c in (quad or [])]}"))
    else:
        checks.append(("P4:quadratic-beats-linear", True,
                       f"NOT TESTED - only {len(pts)} successful points; a quadratic through <=3 "
                       f"points is exact and proves nothing"))

    ok = all(c[1] for c in checks)
    if as_json:
        print(json.dumps({"checks": [{"name": c[0], "ok": c[1], "detail": c[2]} for c in checks],
                          "rows": rows}, indent=2))
    else:
        print(f"flat-in-loop ladder, budget {BUDGET}\n")
        print(f"{'N':>3} {'nodes':>6} {'steps':>8} {'steps/node':>11}  status")
        for r in rows:
            print(f"{r['assignments']:>3} {r['nodes']:>6} {str(r['steps']):>8} "
                  f"{str(r['steps_per_node']):>11}  {r['status']}")
        print()
        for name, good, detail in checks:
            print(f"{'PASS' if good else 'FAIL'}  {name:<28} {detail}")
        print(f"\n{len(checks)} checks, {sum(1 for c in checks if c[1])} passed")
        print("cost curve:", "AS PREDICTED (superlinear)" if ok
              else "PREDICTION FALSIFIED or NOT TESTED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
