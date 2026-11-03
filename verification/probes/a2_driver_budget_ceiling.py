"""A2 driver budget ceiling — where the Pep-written lexer driver runs out of steps.

`lex_source` runs inside the fixed 100,000-step tool budget. This probe measures the
largest generated Pep program the driver can still tokenise, and compares it with
the seed's front end on the same source. It answers one question with numbers:
is a real lexer driver usable at realistic input sizes today, or is it blocked by
the budget (a "valid feature blocked by budget", not a wrong token)?

Fixture shape: `let a0 = 0;\nlet a1 = 1;\n…` — valid Pep at top level, one
identifier/integer/symbol token group per line, so token count ≈ 5 per statement.

Exit codes: 0 = driver tokenised every size up to the largest tried,
1 = the driver refused a size the seed accepts (recorded ceiling),
2 = harness error.
Usage: python a2_driver_budget_ceiling.py <a2-worktree-at-pin> [max_statements]
"""
import pathlib
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_STATEMENTS = int(sys.argv[2]) if len(sys.argv) > 2 else 64
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"
PEP_PS1 = REPO / "pep.ps1"

PROBES = """
fn a3_budget_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""


def program(statements: int) -> bytes:
    lines = [f"let a{index} = {index};" for index in range(statements)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def seed_status(source: bytes):
    with tempfile.TemporaryDirectory(prefix="a3-budget-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source)
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        import json
        payload = json.loads(done.stdout.strip())
    except Exception:  # noqa: BLE001
        return f"NON_JSON(exit={done.returncode})"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def register(session, document, revision, sample_document, sample_revision):
    target_spec = {"document": sample_document, "revision": sample_revision,
                   "entryFunctions": []}
    eof = typed_record_value("LexToken", [
        ("kind", typed("Str", "eof")), ("text", typed("Str", "")),
        ("integerValue", typed("Int", "0")),
        ("stringParts", {"type": "List[Str]", "value": []}),
        ("startByte", typed("Int", "0")), ("endByte", typed("Int", "0")),
        ("line", typed("Int", "1")), ("column", typed("Int", "1")),
    ])
    registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_register", "tool": "a3-budget",
                               "document": document, "revision": revision,
                               "function": "a3_budget_probe"})
    require(registered, "status", "Registered", "register a3-budget")
    validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": "a3-budget",
                              "document": document, "revision": revision,
                              "testVectors": [{
                                  "arguments": [],
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
    require(validated, "status", "Validated", "validate a3-budget")
    activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": "a3-budget",
                              "document": document, "revision": revision})
    require(activated, "status", "Active", "activate a3-budget")


def main():
    print(f"REPO={REPO}")
    sizes = [1, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, MAX_STATEMENTS]
    sizes = sorted({size for size in sizes if 1 <= size <= MAX_STATEMENTS})
    session = Session()
    rows = []
    try:
        opened = session.send({"schemaVersion": 3, "op": "open",
                               "source": SCAN.read_text(encoding="utf-8") + PROBES,
                               "name": "a3-budget-scan", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        register(session, opened["document"], opened["revision"],
                 sample["document"], sample["revision"])

        for statements in sizes:
            source = program(statements)
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"a3-budget-{statements}",
                                   "bytes": list(source)})
            require(target, "outcome", "ok", "open payload")
            started = time.perf_counter()
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "a3-budget",
                                     "arguments": [],
                                     "semanticTarget": {"document": target["document"],
                                                        "revision": target["revision"],
                                                        "entryFunctions": []}})
            elapsed = (time.perf_counter() - started) * 1000
            if response.get("outcome") != "ok":
                code = (response.get("error") or {}).get("code")
                rows.append({"statements": statements, "bytes": len(source),
                             "driver": code, "ms": round(elapsed), "seed": "-"})
                print(f"statements={statements:>3} bytes={len(source):>5} "
                      f"driver={code} ({elapsed:.0f} ms)")
                continue
            tokens = response["result"]["fields"]
            count = 0
            for item in tokens:
                if item["name"] == "tokens":
                    count = len(item["value"]["value"])
            seed = seed_status(source)
            rows.append({"statements": statements, "bytes": len(source), "driver": "ok",
                         "tokens": count, "ms": round(elapsed), "seed": seed})
            print(f"statements={statements:>3} bytes={len(source):>5} driver=ok "
                  f"tokens={count} ({elapsed:.0f} ms) seed={seed}")

        refused = [row for row in rows if row["driver"] != "ok"]
        largest_ok = max([row["statements"] for row in rows if row["driver"] == "ok"],
                         default=0)
        first_refused = refused[0] if refused else None
        print(f"\nlargest tokenised: {largest_ok} statements "
              f"({largest_ok * 14} bytes approx)")
        if first_refused:
            print(f"first refusal: {first_refused['statements']} statements, "
                  f"{first_refused['bytes']} bytes -> {first_refused['driver']} "
                  f"(seed on the same source: {seed_status(program(first_refused['statements']))})")
        print("SUMMARY rows=%d refused=%d" % (len(rows), len(refused)))
    finally:
        session.close()
    return 1 if any(row["driver"] != "ok" for row in rows) else 0


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
