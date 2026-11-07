"""A3 BOOT-A3-028: where do the C23 emitter's execution steps actually go?

Context: BOOT-A3-027 proved that removing the empty-`then` capability gate is NOT enough — A4's
44-node `main` still exceeds the 100k step budget. A2 needs a *measured* attribution, not the
A3 suspicion that "nesting depth is probably the cause".

Instrument: the seed session exposes `{"op":"metrics"}` -> `last_execute_steps`, described in
pep_ocaml.ml as "interpreter steps consumed by the most recent execute ... they exist so per-phase
cost is measurable from outside without instrumenting a scratch worktree". It is reset at the start
of every `execute` and incremented per evaluated checked node. So each chunk emission yields an
exact step count, whether it succeeds or trips the budget.

Method: emit ONE chunk (main) per variant, then read metrics. Two families:
  F*  flat       - N sequential assignments in the function body, depth 1
  D*  nested     - a `while` containing `if` / `if`+`if` / `if`+`if`+`if`
If steps rise steeply with depth at comparable node counts, cost is depth/shape-driven (consistent
with `for branchStatement in nodes` running inside nested lowering). If steps track nodes only,
cost is size-driven. The measurement decides; the suspicion does not.

HONEST LABELS
- This runs against a tree whose emitter has the empty-`then` guard relaxed (BOOT-A3-027's 2-line
  experiment) so every shape clears the capability gate and only COST is measured. The tree is a
  disposable A3 worktree; the patch is not pushed and is not A2's code.
- Variants are A3-authored probes of the emitter, not language test cases and not claims about any
  program's meaning. Only `nodes`, `steps` and emitted/refused are reported.
- The 100k cap is unchanged and A3 proposes no cap change.

Run: python verification/probes/emitter_cost_028.py [--json]
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


def flat(n):
    body = "\n".join("  n = n + 1" for _ in range(n))
    return ("fn main(source: SourceBytes) -> Int {\n"
            "  var n = 0\n" + body + "\n  return n\n}\n")


def nested(depth):
    """depth 1: while{if}  depth 2: while{if{if}}  depth 3: while{if{if{if}}}"""
    lines = ["fn main(source: SourceBytes) -> Int {", "  var n = 0", "  var o = 0",
             "  while !(byte_length(source) <= o) {"]
    indent = "    "
    for level in range(depth):
        lines.append(f"{indent}if o == {level} {{")
        indent += "  "
    lines.append(f"{indent}n = n + 1")
    for level in range(depth):
        indent = indent[:-2]
        lines.append(f"{indent}}} else {{")
        lines.append(f"{indent}  n = n + 2")
        lines.append(f"{indent}}}")
    lines += ["    o = o + 1", "  }", "  return n", "}"]
    return "\n".join(lines) + "\n"


def loop_flat(n):
    """Same `while` envelope as the nested family, but the body is N flat assignments."""
    body = "\n".join("    n = n + 1" for _ in range(n))
    return ("fn main(source: SourceBytes) -> Int {\n"
            "  var n = 0\n"
            "  var o = 0\n"
            "  while !(byte_length(source) <= o) {\n" + body + "\n"
            "    o = o + 1\n"
            "  }\n"
            "  return n\n}\n")


VARIANTS = [
    ("F02", "flat 2 assignments", flat(2)),
    ("F04", "flat 4 assignments", flat(4)),
    ("F08", "flat 8 assignments", flat(8)),
    ("F12", "flat 12 assignments", flat(12)),
    ("L04", "while { 4 flat assignments }", loop_flat(4)),
    ("L08", "while { 8 flat assignments }", loop_flat(8)),
    ("L12", "while { 12 flat assignments }", loop_flat(12)),
    ("D1", "while { if/else }", nested(1)),
    ("D2", "while { if { if/else } }", nested(2)),
    ("D3", "while { if { if { if/else } } }", nested(3)),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def measure(session, helper, target, sem, src, revision):
    """Chunk main, check it, emit it, and return (nodes, steps, status, message)."""
    parsed = parse_target(session, src, target, revision)
    pf = fm(parsed)
    nodes = pf["nodes"]["value"]
    index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
    node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                and helper.nval(n, "text") == "main")
    subtree = index.subtree(int(helper.nval(node, "id")))
    chunk_nodes = index.nodes_for(sorted(subtree))
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
    if checked.get("outcome") != "ok":
        return len(chunk_nodes), None, "check-error", str(checked.get("error"))[:120]
    report = checked["result"]
    if fm(report)["status"]["value"] != "valid":
        return len(chunk_nodes), None, "check-invalid", str(fm(report).get("diagnostics"))[:120]

    emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-unit",
                            "arguments": [sl, report, typed("Int", 0)],
                            "semanticTarget": sem})
    metrics = session.send({"schemaVersion": 3, "op": "metrics"})
    steps = (metrics.get("metrics") or {}).get("last_execute_steps")
    if emitted.get("outcome") != "ok":
        code = (emitted.get("error") or {}).get("code")
        return len(chunk_nodes), steps, f"REFUSED {code}", \
            str((emitted.get("error") or {}).get("message"))[:120]
    ef = fm(emitted["result"])
    if ef["status"]["value"] != "emitted":
        return len(chunk_nodes), steps, "unsupported", str(ef["diagnostic"]["value"])[:120]
    return len(chunk_nodes), steps, "emitted", f"{len(''.join(p['value'] for p in ef['sourceParts']['value']))} bytes C"


def main():
    as_json = "--json" in sys.argv
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    rows, failures = [], 0
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

        for tag, label, src in VARIANTS:
            srcb = src.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": f"cost-{tag}",
                                   "bytes": list(srcb)})
            require(target, "outcome", "ok", f"open {tag}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": ["main"]}
            n_nodes, steps, status, detail = measure(session, helper, target, sem, srcb,
                                                     revision)
            per = (steps / n_nodes) if steps and n_nodes else None
            rows.append({"variant": tag, "shape": label, "nodes": n_nodes, "steps": steps,
                         "steps_per_node": round(per, 1) if per else None,
                         "status": status, "detail": detail})
    finally:
        session.close()

    if as_json:
        print(json.dumps({"budget": BUDGET, "rows": rows}, indent=2))
    else:
        print(f"emitter step cost per single-function chunk (budget {BUDGET})\n")
        print(f"{'variant':8} {'shape':30} {'nodes':>6} {'steps':>8} {'steps/node':>11}  status")
        for r in rows:
            print(f"{r['variant']:8} {r['shape']:30} {r['nodes']:>6} "
                  f"{str(r['steps']):>8} {str(r['steps_per_node']):>11}  {r['status']}")
            if r["status"] != "emitted":
                print(f"{'':8} -> {r['detail']}")
        by = {r["variant"]: r for r in rows}
        print("\nLoop-family comparisons (the only valid attribution):")
        for tag in ("D1", "D2", "L04", "L08"):
            r = by.get(tag)
            if r:
                print(f"  {tag:4} {r['shape']:32} {r['nodes']:>3} nodes -> "
                      f"{str(r['steps']):>7} steps  {r['status']}")
        print("\n  CAREFUL: the F* rows are `unsupported` because a function body without a loop is")
        print("  not a supported shape. Their step counts are PARTIAL work before that refusal, so")
        print("  they must NOT be compared against a loop variant as if they measured nesting.")
        print("  An earlier draft of this summary did exactly that; it was wrong and was removed.")
        print("\nReference: A4's pinned application main = 44 nodes; BOOT-A3-027 measured it "
              f"exceeding the budget once the capability gate was removed.")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
