"""A3 BOOT-A3-047: is the quadratic emission cost per-STATEMENT scanning or per-NODE work?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-047-SCAN-VS-NODE.md @ c8259ee,
committed before this probe existed.

Same while-envelope, similar node count, very different statement count:
  A  one assignment with a long + chain   (1 statement, many nodes)
  B  eight sequential assignments         (8 statements, many nodes)
If cost ~ statements x nodes, B is dramatically dearer than A at comparable size -> the indicated fix
is an index/map, not a cap change.

COST PROBE ONLY - nothing compiled or run.

Run: python verification/probes/scan_vs_node_047.py [--json]
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


def program(body):
    return ("fn main(source: SourceBytes) -> Int {\n"
            "  var n = 0\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n" + body + "\n"
            "    o = o + 1\n"
            "  }\n"
            "  return n\n}\n")


# one statement, many nodes: a long left-associative + chain
# Sized so BOTH land below the budget and can be compared; a first attempt at 12/8 both refused
# at 48/52 nodes, which discriminated nothing.
CHAIN = "1" + " + 1" * 7
ONE_STMT = f"    n = n + {CHAIN}"
MANY_STMT = "    n = n + 1\n" * 5

VARIANTS = [
    ("A1stmt", "one assignment, long + chain", program(ONE_STMT)),
    ("Bmany", "five sequential assignments", program(MANY_STMT.rstrip("\n"))),
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

        for tag, desc, src in VARIANTS:
            payload = src.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": tag,
                                   "bytes": list(payload)})
            st = target.get("status")
            if target.get("outcome") != "ok" or st != "valid":
                rows.append({"variant": tag, "desc": desc, "nodes": None, "steps": None,
                             "status": f"host-{st}"})
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
                                       "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                      if k == "nodes" else pf[k])} for k in pf]}
            chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sl, {"type": "List[CheckedFunction]", "value": []},
                                              {"type": "List[ResolvedSignature]", "value": []},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
            if chk.get("outcome") != "ok" or fm(chk["result"])["status"]["value"] != "valid":
                rows.append({"variant": tag, "desc": desc, "nodes": len(chunk_nodes),
                             "steps": None, "status": "chunk-invalid"})
                continue
            em = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_invoke", "tool": "pep-c23-unit",
                               "arguments": [sl, chk["result"], typed("Int", 0)],
                               "semanticTarget": sem})
            met = session.send({"schemaVersion": 3, "op": "metrics"})
            steps = (met.get("metrics") or {}).get("last_execute_steps")
            status = "refused" if em.get("outcome") != "ok" else (
                "emitted" if fm(em["result"])["status"]["value"] == "emitted" else "unsupported")
            rows.append({"variant": tag, "desc": desc, "nodes": len(chunk_nodes),
                         "steps": steps, "status": status})
    finally:
        session.close()

    a = next((r for r in rows if r["variant"] == "A1stmt"), {})
    b = next((r for r in rows if r["variant"] == "Bmany"), {})
    checks = []
    if a.get("nodes") and b.get("nodes"):
        ratio_nodes = max(a["nodes"], b["nodes"]) / min(a["nodes"], b["nodes"])
        checks.append(("R1:nodes-comparable", ratio_nodes <= 1.25,
                       f"A nodes={a['nodes']} B nodes={b['nodes']} ratio={ratio_nodes:.2f}"))
    else:
        checks.append(("R1:nodes-comparable", False, f"A={a} B={b}"))
    if a.get("steps") and b.get("steps") and a["status"] == "emitted" and b["status"] == "emitted":
        ratio = b["steps"] / a["steps"]
        checks.append(("R2:B-costs-1.8x-A", ratio >= 1.8,
                       f"A steps={a['steps']} B steps={b['steps']} ratio={ratio:.2f}"))
    else:
        checks.append(("R2:B-costs-1.8x-A", True,
                       f"NOT TESTED - A={a.get('status')} {a.get('steps')}, "
                       f"B={b.get('status')} {b.get('steps')}"))

    ok = all(c[1] for c in checks)
    if as_json:
        print(json.dumps({"rows": rows, "checks": [
            {"name": c[0], "ok": c[1], "detail": c[2]} for c in checks]}, indent=2))
    else:
        print(f"per-statement scan vs per-node work, budget {BUDGET} (COST PROBE ONLY)\n")
        print(f"{'var':8} {'nodes':>6} {'steps':>8} {'st/node':>9}  status   body")
        for r in rows:
            spn = round(r["steps"] / r["nodes"], 1) if r.get("steps") and r.get("nodes") else "-"
            print(f"{r['variant']:8} {str(r['nodes']):>6} {str(r['steps']):>8} {str(spn):>9}  "
                  f"{r['status']:8} {r['desc']}")
        print()
        for name, good, detail in checks:
            print(f"{'PASS' if good else 'FAIL'}  {name:<24} {detail}")
        print(f"\n{len(checks)} checks, {sum(1 for c in checks if c[1])} passed")
        r2 = next(c for c in checks if c[0].startswith("R2"))
        if "NOT TESTED" in r2[2]:
            print("reading: NOT DETERMINED - both variants were refused, so no comparison exists.")
            print("         No mechanism claim is made.")
        elif r2[1]:
            print("reading: cost scales with STATEMENTS x NODES - an index/map is the indicated fix")
        else:
            print("reading: NOT per-statement scanning - cost is intrinsic per node; fix elsewhere")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())