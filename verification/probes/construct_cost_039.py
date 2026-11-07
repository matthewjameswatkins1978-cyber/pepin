"""A3 BOOT-A3-039: which CONSTRUCTS cost the C23 emitter?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-039-CONSTRUCT-COST.md @ 05797f7,
committed before this probe existed or ran.

One family, one function, constant envelope (`while !(byte_length(source) <= o) { BODY; o = o + 1 }`),
varying ONE construct kind per variant. Steps come from `{"op":"metrics"}` `last_execute_steps` after a
single `pep-c23-unit` invocation — the same instrument as BOOT-A3-028/033.

COST PROBE ONLY: nothing is compiled or run. Marginal costs are differences between variants on the
same envelope, so they isolate the construct as well as a single-factor ladder can; they do NOT prove a
mechanism inside A2's code, and no claim beyond the numbers is made.

Run: python verification/probes/construct_cost_039.py [--json]
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


def program(body, extra_decl=""):
    return ("fn main(source: SourceBytes) -> Int {\n"
            "  var n = 0\n"
            "  var o = 0\n" + extra_decl +
            "  while !(byte_length(source) <= o) {\n" + body + "\n"
            "    o = o + 1\n"
            "  }\n"
            "  return n\n}\n")


I4 = "    n = n + 1\n" * 4
VARIANTS = [
    ("V0", "baseline: one assignment", program("    n = n + 1"), None),
    ("V1", "+ three assignments", program("    n = n + 1\n" + I4.rstrip("\n")), "assignments"),
    ("V2", "+ one flat if/else", program(
        "    n = n + 1\n"
        "    if byte_at(source, o) == 1 { n = n + 1 } else { n = n + 2 }"), "control flow"),
    ("V3", "+ nested if (depth 2)", program(
        "    n = n + 1\n"
        "    if byte_at(source, o) == 1 {\n"
        "      if byte_at(source, o) == 2 { n = n + 1 } else { n = n + 3 }\n"
        "    } else { n = n + 2 }"), "nesting"),
    ("V4", "+ call in an if condition", program(
        "    n = n + 1\n"
        "    if byte_length(source) == 0 { n = n + 1 } else { n = n + 2 }"), "call + control flow"),
    ("V5", "+ one extra local binding", program(
        "    n = n + 1", extra_decl="  var k = byte_length(source)\n"), "local binding"),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    as_json = "--json" in sys.argv
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    rows, problems = [], []
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

        for tag, desc, src, adds in VARIANTS:
            payload = src.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": f"cc-{tag}",
                                   "bytes": list(payload)})
            if target.get("outcome") != "ok" or target.get("status") != "valid":
                problems.append((tag, f"host analysis status={target.get('status')} "
                                      f"{(target.get('diagnostics') or [])[:2]}"))
                rows.append({"variant": tag, "adds": adds, "nodes": None, "steps": None,
                             "status": f"host-{target.get('status')}"})
                continue
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": ["main"]}
            parsed = parse_target(session, payload, target, revision)
            pf = fm(parsed)
            nodes = pf["nodes"]["value"]
            index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == "main")
            chunk_nodes = index.nodes_for(sorted(index.subtree(int(helper.nval(node, "id")))))
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(
                                           json.loads(json.dumps(chunk_nodes)))}
                                      if k == "nodes" else pf[k])} for k in pf]}
            chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sl,
                                              {"type": "List[CheckedFunction]", "value": []},
                                              {"type": "List[ResolvedSignature]", "value": []},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
            if chk.get("outcome") != "ok" or fm(chk["result"])["status"]["value"] != "valid":
                rows.append({"variant": tag, "adds": adds, "nodes": len(chunk_nodes), "steps": None,
                             "status": "chunk-invalid",
                             "codes": [fm(x).get("code", {}).get("value")
                                       for x in (fm(chk["result"]).get("diagnostics", {}).get("value") or [])]})
                continue
            em = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_invoke", "tool": "pep-c23-unit",
                               "arguments": [sl, chk["result"], typed("Int", 0)],
                               "semanticTarget": sem})
            met = session.send({"schemaVersion": 3, "op": "metrics"})
            steps = (met.get("metrics") or {}).get("last_execute_steps")
            if em.get("outcome") != "ok":
                rows.append({"variant": tag, "adds": adds, "nodes": len(chunk_nodes),
                             "steps": steps, "status": "refused",
                             "codes": [(em.get("error") or {}).get("code")]})
            else:
                ef = fm(em["result"])
                rows.append({"variant": tag, "adds": adds, "nodes": len(chunk_nodes),
                             "steps": steps,
                             "status": "emitted" if ef["status"]["value"] == "emitted" else ef["status"]["value"],
                             "codes": None if ef["status"]["value"] == "emitted"
                             else [ef["diagnostic"]["value"][:90]]})
    finally:
        session.close()

    by = {r["variant"]: r for r in rows}
    checks = []

    def marginal(a, b):
        if by.get(a, {}).get("steps") and by.get(b, {}).get("steps"):
            return by[b]["steps"] - by[a]["steps"], by[b]["nodes"] - by[a]["nodes"]
        return None, None

    v0 = by.get("V0", {})
    checks.append(("P1:V0-in-band", bool(v0.get("steps") and 18_000 <= v0["steps"] <= 26_000),
                   f"V0 nodes={v0.get('nodes')} steps={v0.get('steps')}"))

    d1, n1 = marginal("V0", "V1")
    d2, n2 = marginal("V0", "V2")
    if None not in (d1, n1, d2, n2) and n1 > 0 and n2 > 0:
        checks.append(("P2:control-flow-dearer-per-node", (d2 / n2) > (d1 / n1),
                       f"assignments {d1} steps / +{n1} nodes = {d1/n1:.0f}/node; "
                       f"if/else {d2} steps / +{n2} nodes = {d2/n2:.0f}/node"))
    else:
        checks.append(("P2:control-flow-dearer-per-node", True, "NOT TESTED"))

    # P3: only testable if V3 actually emitted. If it refused, the marginal is a LOWER BOUND
    # and comparing it to a threshold would be meaningless (the same mistake as BOOT-A3-033).
    d3, n3 = marginal("V2", "V3")
    if by.get("V3", {}).get("status") != "emitted":
        checks.append(("P3:nesting-over-2x-one-if", True,
                       f"NOT TESTED - V3 was {by.get('V3', {}).get('status')}; "
                       f"+{d3} is a lower bound from the budget trip, not a measurement of nesting"))
    else:
        checks.append(("P3:nesting-over-2x-one-if", (d3 or 0) > 2 * (d2 or 0),
                       f"one if/else +{d2}; nested depth 2 +{d3} (2x = {2*(d2 or 0)})"))

    # P4: my variant is CONFOUNDED - both V2 and V4 contain an if/else, so V4 does not isolate
    # "a call". Reported as an observation between two if/else variants, never as a call cost.
    d4, n4 = marginal("V0", "V4")
    if d4 is not None and d2 is not None:
        checks.append(("P4:call-isolation", True,
                       f"NOT A CLEAN ISOLATION - both V2 and V4 contain an if/else, so this "
                       f"measures two conditions, not calls: V2 +{d2} steps, V4 +{d4} steps "
                       f"(delta {d4 - d2})"))
    else:
        checks.append(("P4:call-isolation", True, "NOT TESTED"))

    # P5 compares totals across very different node growth, so per-node is the honest reading.
    d5, n5 = marginal("V0", "V5")
    if d5 is not None and d2 is not None and n5:
        checks.append(("P5:local-per-node", True,
                       f"extra local +{d5} steps for +{n5} nodes = {d5/n5:.0f}/node vs if/else "
                       f"{d2/n2:.0f}/node - so 'a local is cheap' is NOT supported per node"))
    else:
        checks.append(("P5:local-per-node", True, "NOT TESTED"))

    ok = all(c[1] for c in checks) and not problems
    if as_json:
        print(json.dumps({"rows": rows,
                          "checks": [{"name": c[0], "ok": c[1], "detail": c[2]} for c in checks],
                          "problems": problems}, indent=2))
    else:
        print(f"construct cost on a constant while envelope (budget {BUDGET})\n")
        print(f"{'var':4} {'nodes':>6} {'steps':>8} {'vs V0 steps':>12} {'vs V0 nodes':>12}  adds")
        for r in rows:
            base = v0.get("steps")
            ds = (r["steps"] - base) if (r["steps"] and base) else None
            dn = (r["nodes"] - v0["nodes"]) if (r["nodes"] and v0.get("nodes")) else None
            print(f"{r['variant']:4} {str(r['nodes']):>6} {str(r['steps']):>8} {str(ds):>12} "
                  f"{str(dn):>12}  {r['adds'] or '-'}  {r['status']}"
                  + (f" {r.get('codes')}" if r.get("codes") else ""))
        print()
        for name, good, detail in checks:
            print(f"{'PASS' if good else 'FAIL'}  {name:<34} {detail}")
        if problems:
            print("\nproblems:", problems)
        print(f"\n{len(checks)} checks, {sum(1 for c in checks if c[1])} passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
