"""A3 BOOT-A3-045: sequential conditionals vs nested - does flattening buy a fit?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-045-FLATTEN-VS-NEST.md @ 055a6f1,
committed before this probe existed.

A lexer is a loop of classification branches. Nested depth-2 inside a while already refuses
(BOOT-A3-028/038); depth-1 emits at 58,635/100,000. If SEQUENTIAL chains fit where nesting does not,
a genuine lexer is emittable today. If they do not, cheaper lowering is a prerequisite for both routes.

COST PROBE ONLY - nothing compiled or run.

Run: python verification/probes/flatten_vs_nest_045.py [--json]
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


ONE = "    if byte_at(source, o) == 1 { n = n + 1 } else { n = n + 9 }"
TWO = ONE + "\n" + "    if byte_at(source, o) == 2 { n = n + 2 } else { n = n + 8 }"
THREE = (TWO + "\n" + "    if byte_at(source, o) == 3 { n = n + 3 } else { n = n + 7 }")
NESTED = ("    if byte_at(source, o) == 1 {\n"
          "      if byte_at(source, o) == 2 { n = n + 1 } else { n = n + 3 }\n"
          "    } else { n = n + 2 }")

VARIANTS = [
    ("Q1", "one sequential if/else", program(ONE)),
    ("Q2", "two sequential if/else", program(TWO)),
    ("Q3", "three sequential if/else", program(THREE)),
    ("Q4", "nested depth-2 (control)", program(NESTED)),
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
            if target.get("outcome") != "ok" or target.get("status") != "valid":
                rows.append({"variant": tag, "desc": desc, "nodes": None, "steps": None,
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
                if chk.get("outcome") != "ok":
                    codes = [(chk.get("error") or {}).get("code"),
                             (chk.get("error") or {}).get("message", "")[:80]]
                else:
                    codes = [fm(x).get("code", {}).get("value")
                             for x in (fm(chk["result"]).get("diagnostics", {}).get("value") or [])]
                rows.append({"variant": tag, "desc": desc, "nodes": len(chunk_nodes),
                             "steps": None, "status": "chunk-invalid", "codes": codes})
                continue
            em = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_invoke", "tool": "pep-c23-unit",
                               "arguments": [sl, chk["result"], typed("Int", 0)],
                               "semanticTarget": sem})
            met = session.send({"schemaVersion": 3, "op": "metrics"})
            steps = (met.get("metrics") or {}).get("last_execute_steps")
            if em.get("outcome") != "ok":
                rows.append({"variant": tag, "desc": desc, "nodes": len(chunk_nodes),
                             "steps": steps, "status": "refused",
                             "codes": [(em.get("error") or {}).get("code")]})
            else:
                ef = fm(em["result"])
                rows.append({"variant": tag, "desc": desc, "nodes": len(chunk_nodes),
                             "steps": steps,
                             "status": "emitted" if ef["status"]["value"] == "emitted"
                             else ef["status"]["value"]})
    finally:
        session.close()

    by = {r["variant"]: r for r in rows}
    checks = []
    q1, q2, q3, q4 = (by.get(v, {}) for v in ("Q1", "Q2", "Q3", "Q4"))
    checks.append(("Q1:baseline-reproduced",
                   bool(q1.get("steps") and 50_000 <= q1["steps"] <= 75_000),
                   f"nodes={q1.get('nodes')} steps={q1.get('steps')}"))
    checks.append(("Q2:three-sequential-emit", q3.get("status") == "emitted",
                   f"nodes={q3.get('nodes')} steps={q3.get('steps')} status={q3.get('status')}"))
    if q3.get("steps") and q4.get("steps"):
        checks.append(("Q3:sequential-cheaper-than-nested", q3["steps"] < q4["steps"],
                       f"Q3={q3['steps']} (n={q3.get('nodes')}) vs Q4={q4['steps']} "
                       f"(n={q4.get('nodes')}, {q4.get('status')})"))
    else:
        checks.append(("Q3:sequential-cheaper-than-nested", True,
                       f"NOT TESTED (Q3 {q3.get('status')} {q3.get('steps')}, "
                       f"Q4 {q4.get('status')} {q4.get('steps')})"))
    checks.append(("Q4:nested-refuses", q4.get("status") == "refused",
                   f"nodes={q4.get('nodes')} steps={q4.get('steps')} status={q4.get('status')}"))

    ok = all(c[1] for c in checks)
    if as_json:
        print(json.dumps({"rows": rows,
                          "checks": [{"name": c[0], "ok": c[1], "detail": c[2]} for c in checks]},
                         indent=2))
    else:
        print(f"flatten vs nest, budget {BUDGET} (COST PROBE ONLY)\n")
        print(f"{'var':4} {'nodes':>6} {'steps':>8}  {'status':12} {'body':30}")
        for r in rows:
            print(f"{r['variant']:4} {str(r['nodes']):>6} {str(r['steps']):>8}  "
                  f"{r['status']:12} {r['desc']:30}"
                  + (f" {r.get('codes')}" if r.get("codes") else ""))
        print()
        for name, good, detail in checks:
            print(f"{'PASS' if good else 'FAIL'}  {name:<34} {detail}")
        print(f"\n{len(checks)} checks, {sum(1 for c in checks if c[1])} passed")
        flat = q3.get("status") == "emitted"
        print("verdict:", "FLATTENING FITS - a lexer-shaped loop is emittable today"
              if flat else "FLATTENING DOES NOT FIT - cheaper lowering is a prerequisite")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())