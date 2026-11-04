"""Boolean-chain cost ladder (Campaign G A3 G-A3-4): a second cost shape besides 66n.

The frozen 66-node gate (62 ok / 64 STEP_LIMIT, stable across 4 candidates) is one
shape. This ladder measures a DIFFERENT canonical compiler-used shape under the
same fixed limits: N-term `&&` conjunctions over integer comparisons — the same
expression class as ascii_digit/ascii_continue (canonical lexer) and the S2/66n
critical path — asking where valid input is refused SOLELY by cost.

Method (consistent with exact_node_ladder.py): whole-parse single chunk through
analyze_chunk_typed with empty externals at the candidate pin; seed oracle per
rung via pep.ps1 check --json. Rungs k = 2,4,...,30 comparisons.

Cases:
  G0  control: smallest rung checks valid (non-vacuity), seed valid.
  G1  observation: the measured boundary (last-ok / first-STEP_LIMIT rung),
      with nodes/terms/bytes per rung. Never a pass/fail gate.
  G2  seed-agreement: every rung is seed-valid, so any staged refusal is
      cost-only, never semantic (claimed).

Exit codes: 0 = held, 1 = falsified, 2 = harness error.
Usage: python boolean_chain_ladder.py <candidate-worktree> [--json PATH]
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
JSON_OUT = None
if "--json" in sys.argv:
    JSON_OUT = pathlib.Path(sys.argv[sys.argv.index("--json") + 1])
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

PEP_PS1 = REPO / "pep.ps1"
RESULTS = []
RUNGS = [2, 4, 6, 8, 10, 12, 16, 20, 24, 30]


def make_source(k):
    terms = " && ".join(f"{i} <= byte" for i in range(k))
    return (f"fn chain(byte: Int) -> Bool {{\n    return {terms}\n}}\n"
            "fn main() -> Int { return 0 }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-booladder-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source.encode("utf-8"))
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"], cwd=str(REPO), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def fields_map(record_value):
    return {item["name"]: item["value"] for item in record_value["fields"]}


def main():
    print(f"REPO={REPO}")
    session = Session()
    output = {"repo": str(REPO), "rungs": {}}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-booladder", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        tool_revision = opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                     done=True, lex_done=True,
                                                     lex_stage="done")
        empty = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty, {"type": "List[CheckedFunction]", "value": []},
              {"type": "List[ResolvedSignature]", "value": []},
              {"type": "List[ResolvedTypeDecl]", "value": []},
              {"type": "Bool", "value": True}], empty_rep),
        ]
        for tool, function, arguments, expect in tools:
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                          "tool": tool, "document": opened["document"],
                          "revision": tool_revision, "function": function})
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": opened["document"],
                                      "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            if validated.get("status") != "Validated":
                print(f"[scope] typed entry point unavailable ({tool}: {validated})")
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                          "tool": tool, "document": opened["document"],
                          "revision": tool_revision})

        rows = []
        for k in RUNGS:
            source = make_source(k)
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"b-{k}",
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open b-{k}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            nodes = -1
            seed = seed_verdict(source)
            try:
                parsed = parse_target(session, source.encode("utf-8"), target,
                                      tool_revision)
                nodes = len(fields_map(parsed)["nodes"]["value"])
            except RuntimeError as err:
                text = str(err)
                code = "PEP_RUNTIME_STEP_LIMIT" if "PEP_RUNTIME_STEP_LIMIT" in text \
                    else f"PARSE-FAIL:{type(err).__name__}"
                state = f"PARSE-{code}" if code.startswith("PEP_") else code
                rows.append({"k": k, "nodes": nodes,
                             "bytes": len(source), "seed": seed, "staged": state})
                output["rungs"][str(k)] = rows[-1]
                print(f"terms={k:3d} nodes={nodes:4d} bytes={len(source):4d} "
                      f"seed={seed} staged={state}")
                continue
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [parsed,
                               {"type": "List[CheckedFunction]", "value": []},
                               {"type": "List[ResolvedSignature]", "value": []},
                               {"type": "List[ResolvedTypeDecl]", "value": []},
                               {"type": "Bool", "value": True}],
                 "semanticTarget": sem})
            if response.get("outcome") != "ok":
                err = response.get("error") or {}
                state = f"TOOL-ERROR/{err.get('code')}"
                rows.append({"k": k, "nodes": nodes, "bytes": len(source),
                             "seed": seed, "staged": state})
                output["rungs"][str(k)] = rows[-1]
                print(f"terms={k:3d} nodes={nodes:4d} bytes={len(source):4d} "
                      f"seed={seed} staged={state}")
                continue
            report = fields_map(response["result"])

            def field_value(record, name):
                value = fields_map(record).get(name) if isinstance(record, dict) else None
                return value.get("value") if isinstance(value, dict) else value

            diagnostics = report["diagnostics"]["value"] if isinstance(
                report.get("diagnostics"), dict) else []
            codes = [field_value(item, "code") for item in diagnostics]
            state = (report["status"]["value"]
                     + (f"/{codes[0]}" if codes else ""))
            rows.append({"k": k, "nodes": nodes, "bytes": len(source),
                         "seed": seed, "staged": state})
            output["rungs"][str(k)] = rows[-1]
            print(f"terms={k:3d} nodes={nodes:4d} bytes={len(source):4d} "
                  f"seed={seed} staged={state}")

        first = rows[0]
        record("G0 smallest rung checks valid", True, "valid",
               first["staged"], f"seed={first['seed']} nodes={first['nodes']}")
        ok_rungs = [r for r in rows if r["staged"] == "valid"]
        bad_rungs = [r for r in rows if r["staged"] != "valid"]
        boundary = (f"last-ok k={ok_rungs[-1]['k']} (nodes={ok_rungs[-1]['nodes']}) / "
                    f"first-refuse k={bad_rungs[0]['k']} (nodes={bad_rungs[0]['nodes']}) "
                    f"state={bad_rungs[0]['staged']}" if ok_rungs and bad_rungs
                    else f"no boundary in range: {[r['staged'] for r in rows]}")
        record("G1 boundary measurement (observation)", False, "observed", boundary)
        seeds_ok = all(r["seed"] == "valid" for r in rows)
        record("G2 every rung is seed-valid (refusal is cost-only)", True, "all-valid",
               "all-valid" if seeds_ok
               else f"SEED-DIFFERS {[ (r['k'], r['seed']) for r in rows if r['seed'] != 'valid' ]}",
               "cost-only attribution holds iff seeds agree")
    finally:
        session.close()

    if JSON_OUT:
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(output, indent=2, sort_keys=True, default=str),
                            encoding="utf-8")
        print(f"json={JSON_OUT}")
    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY claims={len(RESULTS)} claim_falsified={len(falsified)}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
