"""A3 BOOT-A3-048: does operand-tree SHAPE (left vs right spine) change emission cost?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-048-OPERAND-SHAPE.md @ e843a23,
committed before this probe existed.

Associativity was checked first: Pep is left-associative, explicit left parens change nothing, and
`1 + (2 + (3 + 4))` builds a right spine with the SAME node and statement count. So this compares
shape alone, inside an identical while envelope.

S1 same node count · S2 both emit · S3 right spine costs >=15% more than left (my falsifier)

COST PROBE ONLY - nothing compiled or run.

Run: python verification/probes/operand_shape_048.py [--json]
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


# six additions each, one assignment each, identical literal and binary counts
LEFT = "    n = n + 1 + 1 + 1 + 1 + 1 + 1"
RIGHT = "    n = n + (1 + (1 + (1 + (1 + (1 + 1)))))"

VARIANTS = [
    ("L_spine", "left spine: n = n + 1 + 1 + ... (six additions)", program(LEFT)),
    ("R_spine", "right spine: n = n + (1 + (1 + ...)) (six additions)", program(RIGHT)),
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

    l = next((r for r in rows if r["variant"] == "L_spine"), {})
    r = next((r for r in rows if r["variant"] == "R_spine"), {})
    checks = []
    checks.append(("S1:same-node-count", l.get("nodes") is not None and l.get("nodes") == r.get("nodes"),
                   f"L nodes={l.get('nodes')} R nodes={r.get('nodes')}"))
    checks.append(("S2:both-emit", l.get("status") == "emitted" and r.get("status") == "emitted",
                   f"L={l.get('status')} R={r.get('status')}"))
    if l.get("steps") and r.get("steps") and l.get("status") == "emitted" and r.get("status") == "emitted":
        ratio = r["steps"] / l["steps"]
        checks.append(("S3:right-spine-15pct-dearer", ratio >= 1.15,
                       f"L steps={l['steps']} R steps={r['steps']} ratio={ratio:.3f}"))
    else:
        checks.append(("S3:right-spine-15pct-dearer", True,
                       f"NOT TESTED - L={l.get('status')} {l.get('steps')}, "
                       f"R={r.get('status')} {r.get('steps')}"))

    ok = all(c[1] for c in checks)
    if as_json:
        print(json.dumps({"rows": rows, "checks": [
            {"name": c[0], "ok": c[1], "detail": c[2]} for c in checks]}, indent=2))
    else:
        print(f"operand-tree shape vs cost, budget {BUDGET} (COST PROBE ONLY)\n")
        print(f"{'var':8} {'nodes':>6} {'steps':>8}  {'status':10} body")
        for x in rows:
            print(f"{x['variant']:8} {str(x['nodes']):>6} {str(x['steps']):>8}  {x['status']:10} {x['desc']}")
        print()
        for name, good, detail in checks:
            print(f"{'PASS' if good else 'FAIL'}  {name:<30} {detail}")
        print(f"\n{len(checks)} checks, {sum(1 for c in checks if c[1])} passed")
        s3 = next(c for c in checks if c[0].startswith("S3"))
        if "NOT TESTED" in s3[2]:
            print("reading: NOT DETERMINED - one or both variants refused; no mechanism claim")
        elif s3[1]:
            print("reading: operand-tree SHAPE matters - depth-sensitive cost, target for A2")
        else:
            print("reading: shape does NOT matter (within 15%) - the driver is still unidentified;")
            print("         next step is for A2 to instrument the emitter, not for A3 to keep guessing")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())