#!/usr/bin/env python3
"""A3-S2: measured step cost per compiler-A function (verification/probes).

A2-S2 must split expensive functions and A1-S2 must size a fragment contract. Both
need the number that decides the split: how many of the frozen 100,000 tool steps a
whole-function chunk check actually consumes.

MEASUREMENT NOTE, because I got this wrong first. `metrics.last_execute_steps` IS the
step cost of the most recent `tool_invoke`. My first version treated it as a cumulative
counter and reported deltas, which produced negative and zero "costs". It does not
accumulate: each invoke overwrites it. Read absolutely, it is stable and repeatable --
verified by running four functions twice in independent sessions, identical both times
(is_digit 37346, is_ws 50104, is_int3 87055, is_ret3 87055).

  PEPIN_GATE_ROOT=<worktree at the emitter pin>
  PEPIN_APP_REL / PEPIN_APP_REV as in emit_any_049.py

Read-only. Exit 0 when the probe completed: the data is the output.
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
from pep_c23 import Session, require, parse_target  # noqa: E402

APP_REL = os.environ.get("PEPIN_APP_REL", "examples/dogfood/pep0/compiler_a.pep")
APP_REV = os.environ.get("PEPIN_APP_REV", "5f62e4b")
BUDGET = int(os.environ.get("PEPIN_STEP_BUDGET", "100000"))
# The session reports budget+1 when a run aborts on the limit.
LIMIT_MARK = BUDGET + 1


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    app = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob",
                          f"{APP_REV}:{APP_REL}"], capture_output=True, check=False).stdout
    if not app:
        print(f"FAIL: cannot read {APP_REV}:{APP_REL}")
        return 2
    print(f"app: {APP_REL} @ {APP_REV} ({len(app)} bytes)  budget: {BUDGET}\n")

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

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "steps",
                               "bytes": list(app)})
        if target.get("status") != "valid":
            print(f"host analysis refuses: {target.get('status')}")
            return 1
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"] if b"fn main(" in app else []}
        parsed = parse_target(session, app, target, revision)
        pf = fm(parsed)
        nodes = pf["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        labels = [helper.nval(n, "text") for n in nodes if helper.nval(n, "kind") == "function"]

        rows = []
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            chunk_nodes = index.nodes_for(sorted(index.subtree(int(helper.nval(node, "id")))))
            other = [s for s in sigs if s["name"] != label]
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                      if k == "nodes" else pf[k])} for k in pf]}
            chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sl,
                                              {"type": "List[CheckedFunction]",
                                               "value": [helper.checked_fn_value(s) for s in other]},
                                              {"type": "List[ResolvedSignature]",
                                               "value": [helper.resolved_sig_value(s) for s in other]},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
            steps = (session.send({"schemaVersion": 3, "op": "metrics"})
                     .get("metrics", {}).get("last_execute_steps"))
            status = ((chk.get("error") or {}).get("code") if chk.get("outcome") != "ok"
                      else fm(chk["result"])["status"]["value"])
            rows.append((label, len(chunk_nodes), status, steps))

        rows.sort(key=lambda r: r[1])
        print(f"{'function':<14}{'nodes':>6}{'status':>24}{'steps':>9}{'steps/node':>12}{'%budget':>9}")
        print("-" * 76)
        completed = []
        for label, n, status, steps in rows:
            if steps is None:
                per = pct = "-"
            elif steps >= LIMIT_MARK:
                per = pct = "LIMIT"
            else:
                per = f"{steps / n:.0f}"
                pct = f"{100.0 * steps / BUDGET:.0f}%"
                completed.append((label, n, steps))
            print(f"{label:<14}{n:>6}{str(status):>24}{str(steps):>9}{per:>12}{pct:>9}")

        if completed:
            top = max(completed, key=lambda r: r[2])
            print(f"\nmost expensive completed function: {top[0]} — {top[2]} steps "
                  f"({100.0 * top[2] / BUDGET:.0f}% of budget) at {top[1]} nodes")
            print(f"headroom at that size           : {BUDGET - top[2]} steps "
                  f"(~{(BUDGET - top[2]) / (top[2] / top[1]):.0f} more nodes at {top[2] / top[1]:.0f}/node)")
            biggest_ok = max(completed, key=lambda r: r[1])
            print(f"largest node count that fits    : {biggest_ok[1]} nodes")
        over = [r for r in rows if r[3] is not None and r[3] >= LIMIT_MARK]
        print(f"functions over budget           : {len(over)} of {len(rows)}")
        print("\nNo curve is fitted. Steps/node is reported per function because A3 has")
        print("previously falsified three cost hypotheses; a fit here would be a guess.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())