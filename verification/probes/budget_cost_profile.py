"""Cost profile by source shape — where the fixed 100k-step budget actually burns.

`shared_budget_mechanism.py` showed both Pep-written lanes stall at ~10^3 steps per
unit on one source family (top-level `let`). This probe asks the follow-up question
that determines whether the 66-node boolean-chain row is representative or unusual:

  for each shape family, how many units does 100,000 steps buy -- and does the
  driver's ceiling stay flat in tokens while the checker's ceiling moves in nodes?

Shapes: plain `let` statements, boolean chains (the 66-node fixture's expression
style), records, small functions, match arms over a union, string literals.

For each shape it records the largest success and the first refusal in units and
bytes, for both lanes, then reports implied steps/unit.

Claims:
  S1  every shape has a measurable ceiling in at least one lane (no shape is free).
  S2  the driver's ceiling is stable in tokens across shapes (per-token cost, not
      per-shape), within a factor of two.
  S3  the checker's cost per node is shape-dependent: the most expensive shape
      needs at least 1.5x fewer units than the cheapest before refusing.
  O1  refused sources are valid to the seed (so the ceiling is the budget, not the
      language).

Local measurement only: run in a scratch tree containing both lanes. Nothing is
published and no candidate is created.

Exit codes: 0 = profile produced and claims held, 1 = a claim falsified,
2 = harness error.
Usage: python budget_cost_profile.py <tree-with-both-lanes> [max_units]
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_RUNG = int(sys.argv[2]) if len(sys.argv) > 2 else 40
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"
PEP_PS1 = REPO / "pep.ps1"
BUDGET = 100_000

DRIVER_PROBES = """
fn a3_profile_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""


def shape_lets(n):
    return ("\n".join(f"let a{i} = {i};" for i in range(n)) + "\n").encode()


def shape_bool_chains(n):
    body = []
    for i in range(n):
        body.append(
            f"fn b{i}(x: Int) -> Bool {{\n"
            f"  return x == {i} && x == {i + 1} || x == {i + 2} || x == {i + 3}\n"
            f"}}")
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def shape_records(n):
    body = [f"type R{i} {{\n    a: Int\n    b: Int\n}}" for i in range(n)]
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def shape_functions(n):
    body = [f"fn f{i}() -> Int {{ return {i} }}" for i in range(n)]
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def shape_match_arms(n):
    variants = " | ".join(f"V{i}(Int)" for i in range(n))
    arms = "\n        ".join(f"V{i}(value) => value" for i in range(n))
    return (f"type E = {variants}\n\n"
            f"fn pick(e: E) -> Int {{\n    return match e {{\n        {arms}\n    }}\n}}\n\n"
            f"fn main() -> Int {{ return 0 }}\n").encode()


def shape_strings(n):
    body = [f"say(\"s{i}\")" for i in range(n)]
    return ("\n".join(body) + "\n").encode()


SHAPES = {
    "lets": shape_lets,
    "bool_chains": shape_bool_chains,
    "records": shape_records,
    "functions": shape_functions,
    "match_arms": shape_match_arms,
    "strings": shape_strings,
}

LADDER = [2, 4, 8, 12, 16, 20, 24, 28, 32, 40]


def seed_status(source: bytes):
    with tempfile.TemporaryDirectory(prefix="a3-profile-") as folder:
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


def make_driver():
    session = Session()
    opened = session.send({"schemaVersion": 3, "op": "open",
                           "source": SCAN.read_text(encoding="utf-8") + DRIVER_PROBES,
                           "name": "a3-profile-scan", "metadataOnly": True})
    require(opened, "outcome", "ok", "open scan module")
    require(opened, "status", "valid", "check scan module")
    sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v", "bytes": []})
    eof = typed_record_value("LexToken", [
        ("kind", typed("Str", "eof")), ("text", typed("Str", "")),
        ("integerValue", typed("Int", "0")),
        ("stringParts", {"type": "List[Str]", "value": []}),
        ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
        ("line", typed("Int", "1")), ("column", typed("Int", "1"))])
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                  "tool": "a3-profile", "document": opened["document"],
                  "revision": opened["revision"], "function": "a3_profile_probe"})
    session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                  "tool": "a3-profile", "document": opened["document"],
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
                  "tool": "a3-profile", "document": opened["document"],
                  "revision": opened["revision"]})
    return session


def make_checker():
    session = Session()
    bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "a3-profile-bundle", "metadataOnly": True})
    require(opened, "outcome", "ok", "open compiler bundle")
    require(opened, "status", "valid", "check compiler bundle")
    sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v", "bytes": []})
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
    finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                 done=True, lex_done=True, lex_stage="done")
    empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
    empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
    for tool, function, arguments, expect in [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"], finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked)]:
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                      "tool": tool, "document": opened["document"],
                      "revision": opened["revision"], "function": function})
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": opened["document"],
                                  "revision": opened["revision"],
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                      "tool": tool, "document": opened["document"],
                      "revision": opened["revision"]})
    return session, opened


def run_driver(session, source):
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": f"a3-p-{len(source)}", "bytes": list(source)})
    require(target, "outcome", "ok", "open driver payload")
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": "a3-profile", "arguments": [],
                             "semanticTarget": {"document": target["document"],
                                                "revision": target["revision"],
                                                "entryFunctions": []}})
    if response.get("outcome") != "ok":
        return {"state": (response.get("error") or {}).get("code"), "units": None}
    tokens = 0
    for item in response["result"]["fields"]:
        if item["name"] == "tokens":
            tokens = len(item["value"]["value"])
    return {"state": "ok", "units": tokens}


def run_checker(session, opened, source):
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": f"a3-c-{len(source)}", "bytes": list(source)})
    require(target, "outcome", "ok", "open checker payload")
    try:
        parsed = parse_target(session, source, target, opened["revision"])
    except BaseException as error:  # noqa: BLE001
        # Collector-level parse failure: `pep_c23.parse_target` caps its own loop by
        # source length, so a slow parse surfaces here as a RuntimeError. Recorded
        # with its message so an instrument limit is never read as a compiler verdict.
        return {"state": f"PARSE:{type(error).__name__}:{str(error)[:90]}", "units": None}
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
        return {"state": (response.get("error") or {}).get("code"), "units": nodes}
    return {"state": "ok", "units": nodes}


def main():
    print(f"REPO={REPO}")
    driver = make_driver()
    checker, opened = make_checker()
    profile = {}
    try:
        for shape, generator in SHAPES.items():
            rows = []
            for rung in LADDER:
                if rung > MAX_RUNG:
                    continue
                source = generator(rung)
                rows.append({"rung": rung, "bytes": len(source),
                             "driver": run_driver(driver, source),
                             "checker": run_checker(checker, opened, source)})
            profile[shape] = rows
            for row in rows:
                print(f"{shape:<12} rung={row['rung']:>3} bytes={row['bytes']:>5} "
                      f"driver={row['driver']['state']:<26} "
                      f"tokens={row['driver']['units']} "
                      f"checker={row['checker']['state']:<26} "
                      f"nodes={row['checker']['units']}")
    finally:
        driver.close()
        checker.close()

    def ceiling(rows, lane):
        ok = [row for row in rows if row[lane]["state"] == "ok"]
        bad = [row for row in rows if row[lane]["state"] != "ok"]
        last = max(ok, key=lambda row: row["rung"]) if ok else None
        return last, (bad[0] if bad else None)

    print("\n== profile summary ==")
    driver_units, checker_units = {}, {}
    for shape, rows in profile.items():
        last_d, bad_d = ceiling(rows, "driver")
        last_c, bad_c = ceiling(rows, "checker")
        if last_d:
            driver_units[shape] = last_d["driver"]["units"]
        if last_c:
            checker_units[shape] = last_c["checker"]["units"]
        print(f"{shape:<12} driver: last ok {last_d['driver']['units'] if last_d else '-'} units "
              f"({last_d['bytes'] if last_d else '-'} B) / first refusal "
              f"{(bad_d['driver']['state'] + ' @' + str(bad_d['bytes']) + ' B') if bad_d else '-'}"
              f"   checker: last ok {last_c['checker']['units'] if last_c else '-'} nodes "
              f"({last_c['bytes'] if last_c else '-'} B) / first refusal "
              f"{(bad_c['checker']['state'] + ' @' + str(bad_c['bytes']) + ' B') if bad_c else '-'}")

    RESULTS = []
    claim_s1 = all(ceiling(rows, "driver")[1] or ceiling(rows, "checker")[1]
                   for rows in profile.values())
    RESULTS.append({"case": "S1 every shape has a measurable ceiling", "claimed": True,
                    "expect": "all shapes bounded", "falsified": not claim_s1,
                    "outcome": "all bounded" if claim_s1 else "a shape never refused"})
    if len(driver_units) >= 2:
        spread = max(driver_units.values()) / max(min(driver_units.values()), 1)
    else:
        spread = 1.0
    claim_s2 = spread <= 2.0
    RESULTS.append({"case": "S2 driver ceiling stable in tokens across shapes",
                    "claimed": True, "expect": "spread<=2.0", "falsified": not claim_s2,
                    "outcome": f"spread={spread:.2f} {json.dumps(driver_units)}"})
    if len(checker_units) >= 2:
        ratio = max(checker_units.values()) / max(min(checker_units.values()), 1)
    else:
        ratio = 1.0
    claim_s3 = ratio >= 1.5
    RESULTS.append({"case": "S3 checker cost per node is shape-dependent",
                    "claimed": True, "expect": "ratio>=1.5", "falsified": not claim_s3,
                    "outcome": f"ratio={ratio:.2f} {json.dumps(checker_units)}"})

    refused = []
    for shape, rows in profile.items():
        last_c, bad_c = ceiling(rows, "checker")
        if bad_c:
            refused.append((shape, seed_status(SHAPES[shape](bad_c["rung"]))))
    RESULTS.append({"case": "O1 refused sources are seed-valid", "claimed": False,
                    "expect": "observed", "outcome": json.dumps(refused),
                    "falsified": False})

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
