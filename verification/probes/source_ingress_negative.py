"""Source-ingress / parser-continuation integrity negatives (Reserve D A3 card).

`analyze_chunk_inner_bound` opens with two ingress guards (source-read at
`81398fa`, `tests/pep_checker_a13.pep` `analyze_chunk_inner_bound`):
  authority = semantic_snapshot()              # the call's live target identity
  parsed.document/revision != authority  ->  invalid + A13_PARSER_REVISION
  !parsed.done                       ->  invalid + A13_PARSER_BUDGET
Only then does checking (and, on later pins, the R-ID-1 gate) run. These cases
prove the guards fire on forged ingress instead of checking stale or unfinished
parses. O1b/O1c already cover stale FACTS; this covers the stale/unfinished
PARSE itself.

Cases (fixed expectations, single pin — the integration gate pin):
  G0  control: honest complete parse of a valid program -> valid.
  G1  stale parse: parse at rev1, advance the target with apply_edit, invoke
      with the old progress against the new revision -> refused.
  G2  unfinished continuation: honest parse with done flipped to false ->
      refused with A13_PARSER_BUDGET.
  G3  foreign-document parse: progress from document A invoked against document
      B -> refused.
Requirement (layer-agnostic): the refusal must carry a provenance code.
Observed layering at 81398fa: the host transport refuses revision-mismatched
invokes itself (tool-level PEP_STALE_REVISION) before the Pep entry guard runs,
so G1/G3 hold at the host layer; the in-language A13_PARSER_REVISION guard is
the second layer. G2 reaches Pep code (stamps match) and must carry
A13_PARSER_BUDGET. The exact layer+code is always printed in the detail.

Exit codes: 0 = all claims held, 1 = a claim falsified (hole), 2 = harness error.
Usage: python source_ingress_negative.py <candidate-worktree> [--json PATH]
"""
import copy
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

SOURCE = ("fn f() -> Int {\n    return 0\n}\n"
          "fn main() -> Int { return 0 }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-ingress-") as folder:
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
    output = {"repo": str(REPO), "cases": {}}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-ingress", "metadataOnly": True})
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

        def invoke(parsed, sem):
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
                return {"verdict": "TOOL-ERROR", "codes": [err.get("code")],
                        "layer": "host"}
            report = fields_map(response["result"])

            def field_value(record, name):
                value = fields_map(record).get(name) if isinstance(record, dict) else None
                return value.get("value") if isinstance(value, dict) else value

            diagnostics = report["diagnostics"]["value"] if isinstance(
                report.get("diagnostics"), dict) else []
            return {"verdict": report["status"]["value"],
                    "codes": [field_value(item, "code") for item in diagnostics],
                    "layer": "pep"}

        REVISION_FAMILY = {"A13_PARSER_REVISION", "PEP_STALE_REVISION"}

        def check(result, code):
            # Hold iff refused with a provenance code: host-layer
            # PEP_STALE_REVISION for revision mismatches, or the exact
            # in-language code. Anything else (valid verdict, semantic codes,
            # unexpected tool errors) reports actual and falsifies.
            codes = [c for c in (result["codes"] or []) if c]
            if result["layer"] == "host":
                if result["verdict"] == "TOOL-ERROR" \
                        and "PEP_STALE_REVISION" in codes \
                        and code in REVISION_FAMILY:
                    return "refused"
                return f"TOOL-ERROR layer=host codes={codes}"
            if result["verdict"] != "valid" and code in codes:
                return "refused"
            return f"verdict={result['verdict']} layer=pep codes={codes}"

        seed = seed_verdict(SOURCE)

        # G0 control.
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "g-src",
                               "bytes": list(SOURCE.encode("utf-8"))})
        require(target, "outcome", "ok", "open g-src")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(session, SOURCE.encode("utf-8"), target, tool_revision)
        r0 = invoke(parsed, sem)
        record("G0 honest complete parse checks normally", True, "valid",
               r0["verdict"], f"seed={seed}")
        output["cases"]["G0"] = {"result": r0, "seed": seed}

        # G1 stale parse: advance the target, reuse the old progress.
        advance = session.send({"schemaVersion": 3, "op": "apply_edit",
                                "document": target["document"],
                                "expected_revision": target["revision"],
                                "start_byte": 0, "end_byte": 0,
                                "replacement": "//x\n"})
        require(advance, "outcome", "ok", "advance revision")
        sem2 = {"document": target["document"], "revision": advance["revision"],
                "entryFunctions": []}
        r1 = invoke(parsed, sem2)
        record("G1 stale parse is refused with a provenance code", True,
               "refused", check(r1, "A13_PARSER_REVISION"),
               "parsed at rev1, target advanced to rev2")
        output["cases"]["G1"] = {"result": r1}

        # G2 unfinished continuation: same stamps, done flipped to false.
        unfinished = copy.deepcopy(parsed)
        for item in unfinished["fields"]:
            if item["name"] == "done":
                item["value"] = {"type": "Bool", "value": False}
        r2 = invoke(unfinished, sem)
        record("G2 unfinished continuation is refused with A13_PARSER_BUDGET", True,
               "refused", check(r2, "A13_PARSER_BUDGET"),
               "stamps match, done=false")
        output["cases"]["G2"] = {"result": r2}

        # G3 foreign-document parse.
        other = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "g-other",
                              "bytes": list(SOURCE.encode("utf-8"))})
        require(other, "outcome", "ok", "open g-other")
        sem_other = {"document": other["document"], "revision": other["revision"],
                     "entryFunctions": []}
        r3 = invoke(parsed, sem_other)
        record("G3 foreign-document parse is refused with a provenance code", True,
               "refused", check(r3, "A13_PARSER_REVISION"),
               "progress of g-src invoked against g-other")
        output["cases"]["G3"] = {"result": r3}
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
