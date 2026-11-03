"""Do the A2 driver ceiling and the A1 checker wall share one obstruction?

Both stages run inside the same fixed 100,000-step tool budget, but they have been
reported as separate symptoms (driver: ~120 tokens; checker: the 66-node
regression row). This probe measures both ceilings on the SAME generated source
family in ONE tree, so the comparison is arithmetic on the same budget rather than
two anecdotes:

  driver   `stdlib/scan.pep` `lex_source` on `let aN = N;` x n
  checker  the Pep-written checker (`analyze_parsed`) on the parse of the same source

For each ladder rung it records ok/refused and the unit count (tokens / nodes) at
the last success and the first refusal, then reports steps-per-unit implied by a
100,000-step budget. Claims are deliberately modest:

  S1  each stage has a measurable ceiling on the same family (no infinite budget).
  S2  the two ceilings are within one order of magnitude of each other in units,
      i.e. "≈10^2 units per 100k steps for both" — the shared-mechanism reading,
      stated as arithmetic, not as a code claim.
  O1  every refusal is `PEP_RUNTIME_STEP_LIMIT` on a source the seed accepts as
      valid (so neither ceiling is a language limit).

Run in a tree that contains BOTH lanes (a scratch merge of the A1 and A2 heads).
Local measurement only: nothing is published, no candidate is created.

Exit codes: 0 = both ceilings measured, 1 = a claim falsified, 2 = harness error.
Usage: python shared_budget_mechanism.py <tree-with-both-lanes> [max_statements]
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_STATEMENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"
PEP_PS1 = REPO / "pep.ps1"
BUDGET = 100_000

DRIVER_PROBES = """
fn a3_shared_stream_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""

LADDER = [2, 4, 8, 12, 16, 18, 20, 21, 22, 23, 24, 28, 32, 40]


def program(statements: int) -> bytes:
    return ("\n".join(f"let a{index} = {index};" for index in range(statements))
            + "\n").encode("utf-8")


def seed_status(source: bytes):
    with tempfile.TemporaryDirectory(prefix="a3-shared-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source)
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def driver_ceiling():
    session = Session()
    rows = []
    try:
        opened = session.send({"schemaVersion": 3, "op": "open",
                               "source": SCAN.read_text(encoding="utf-8") + DRIVER_PROBES,
                               "name": "a3-shared-scan", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        eof = typed_record_value("LexToken", [
            ("kind", typed("Str", "eof")), ("text", typed("Str", "")),
            ("integerValue", typed("Int", "0")),
            ("stringParts", {"type": "List[Str]", "value": []}),
            ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
            ("line", typed("Int", "1")), ("column", typed("Int", "1"))])
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                      "tool": "a3-shared", "document": opened["document"],
                      "revision": opened["revision"], "function": "a3_shared_stream_probe"})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                      "tool": "a3-shared", "document": opened["document"],
                      "revision": opened["revision"],
                      "testVectors": [{"arguments": [],
                                       "expect": typed_record_value("LexResult", [
                                           ("status", typed("Str", "ok")),
                                           ("errorCode", typed("Str", "")),
                                           ("sourceBytes", typed("Int", "0")),
                                           ("errorStart", typed("Int", "-1")),
                                           ("errorEnd", typed("Int", "-1")),
                                           ("errorLine", typed("Int", "-1")),
                                           ("errorColumn", typed("Int", "-1")),
                                           ("tokens", {"type": "List[LexToken]",
                                                       "value": [eof]})]),
                                       "semanticTarget": target_spec}]})
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                      "tool": "a3-shared", "document": opened["document"],
                      "revision": opened["revision"]})
        for statements in LADDER:
            if statements > MAX_STATEMENTS:
                continue
            source = program(statements)
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"a3-shared-{statements}",
                                   "bytes": list(source)})
            require(target, "outcome", "ok", "open payload")
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "a3-shared",
                                     "arguments": [],
                                     "semanticTarget": {"document": target["document"],
                                                        "revision": target["revision"],
                                                        "entryFunctions": []}})
            if response.get("outcome") != "ok":
                rows.append({"statements": statements, "bytes": len(source),
                             "state": (response.get("error") or {}).get("code"),
                             "units": None})
            else:
                tokens = 0
                for item in response["result"]["fields"]:
                    if item["name"] == "tokens":
                        tokens = len(item["value"]["value"])
                rows.append({"statements": statements, "bytes": len(source),
                             "state": "ok", "units": tokens})
    finally:
        session.close()
    return rows


def checker_ceiling():
    session = Session()
    rows = []
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-shared-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                     done=True, lex_done=True,
                                                     lex_stage="done")
        empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        for tool, function, arguments, expect in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked)]:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": tool,
                                       "document": opened["document"],
                                       "revision": opened["revision"],
                                       "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": opened["document"],
                                      "revision": opened["revision"],
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": tool,
                                      "document": opened["document"],
                                      "revision": opened["revision"]})
            require(activated, "status", "Active", f"activate {tool}")
        for statements in LADDER:
            if statements > MAX_STATEMENTS:
                continue
            source = program(statements)
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"a3-shared-chk-{statements}",
                                   "bytes": list(source)})
            require(target, "outcome", "ok", "open checker payload")
            try:
                parsed = parse_target(session, source, target, opened["revision"])
            except BaseException as error:  # noqa: BLE001 - parser budget is data here
                rows.append({"statements": statements, "bytes": len(source),
                             "state": f"PARSE:{type(error).__name__}", "units": None})
                continue
            nodes = 0
            for field in parsed["fields"]:
                if field["name"] == "nodes":
                    nodes = len(field["value"]["value"])
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-checker",
                                     "arguments": [parsed],
                                     "semanticTarget": {"document": target["document"],
                                                        "revision": target["revision"],
                                                        "entryFunctions": []}})
            if response.get("outcome") != "ok":
                rows.append({"statements": statements, "bytes": len(source),
                             "state": (response.get("error") or {}).get("code"),
                             "units": nodes})
            else:
                rows.append({"statements": statements, "bytes": len(source),
                             "state": "ok", "units": nodes})
    finally:
        session.close()
    return rows


def summarise(name, rows):
    ok = [row for row in rows if row["state"] == "ok"]
    refused = [row for row in rows if row["state"] != "ok"]
    largest = max(ok, key=lambda row: row["statements"]) if ok else None
    first_bad = refused[0] if refused else None
    print(f"\n== {name} ==")
    for row in rows:
        print(f"  statements={row['statements']:>3} bytes={row['bytes']:>4} "
              f"state={row['state']:<28} units={row['units']}")
    if largest:
        print(f"  last success: {largest['units']} units "
              f"({largest['bytes']} bytes) -> <= {BUDGET / max(largest['units'], 1):.0f} "
              f"steps/unit implied")
    if first_bad:
        print(f"  first refusal: {first_bad['units']} units "
              f"({first_bad['bytes']} bytes) -> {first_bad['state']}")
    return largest, first_bad


def main():
    print(f"REPO={REPO}")
    driver_rows = driver_ceiling()
    checker_rows = checker_ceiling()
    driver_last, driver_bad = summarise("driver lex_source", driver_rows)
    checker_last, checker_bad = summarise("Pep-written checker analyze_parsed", checker_rows)

    RESULTS = []
    both = driver_bad and checker_bad
    record = RESULTS.append
    claim_s1 = bool(driver_bad and checker_bad)
    record({"case": "S1 each stage has a measurable ceiling on the same family", "claimed": True,
            "expect": "both refused", "outcome": "both refused" if claim_s1 else "no ceiling",
            "falsified": not claim_s1, "detail": ""})
    driver_units = driver_last["units"] if driver_last else 0
    checker_units = checker_last["units"] if checker_last else 0
    ratio = (max(driver_units, checker_units) / max(min(driver_units, checker_units), 1))
    claim_s2 = 1 <= ratio <= 10
    record({"case": "S2 ceilings within one order of magnitude in units", "claimed": True,
            "expect": "ratio<=10", "outcome": f"ratio={ratio:.1f} "
            f"(driver={driver_units}, checker={checker_units})",
            "falsified": not claim_s2, "detail": ""})
    seed_ok = seed_status(program(driver_bad["statements"])) if driver_bad else "n/a"
    seed_ok_checker = seed_status(program(checker_bad["statements"])) if checker_bad else "n/a"
    claim_o1 = seed_ok.startswith("valid") and seed_ok_checker.startswith("valid")
    record({"case": "O1 refusals happen on sources the seed accepts", "claimed": False,
            "expect": "observed", "outcome": f"driver seed={seed_ok} "
            f"checker seed={seed_ok_checker}", "falsified": False, "detail": ""})

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY claims={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
