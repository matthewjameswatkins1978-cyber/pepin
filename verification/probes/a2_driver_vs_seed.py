"""A2 lexer-driver differential against the OCaml seed — adversarial inputs, seed as oracle.

A2's own suite compares the driver to the canonical Pep lexer
(`examples/pep_lexer.pep`). This probe deliberately uses the **seed** instead, so
the oracle is independent of the reference both sides already agree on. For each
fixture the seed's own front end (`pep.ps1 check --json`) supplies status, code,
byte offset, line and column; the driver (`lex_source`) supplies its LexResult.

Claims:
  E1  error-code + offset parity: when the seed reports a lexer-family
      diagnostic, the driver reports the same code at the same start byte.
  E2  valid-source parity: when the seed accepts the source, the driver's status
      is `ok` with no error code.
  E3  position parity: driver `errorLine`/`errorColumn` equal the seed's
      line/column for the same byte offset (CRLF, tab and multi-line fixtures).
  O1  (observation) bare `?` — the seed reports `incomplete` (a hole); recorded,
      not claimed, because `incomplete` is a front-end state rather than a lexer
      verdict.

Exit codes: 0 = all claims hold, 1 = a claim falsified, 2 = harness error.
Usage: python a2_driver_vs_seed.py <a2-worktree-at-pin>
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"
PEP_PS1 = REPO / "pep.ps1"

PROBES = """
fn a3_lex_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""

LEXER_CODES = ("PEP_UNEXPECTED_CHARACTER", "PEP_INVALID_ESCAPE",
               "PEP_UNTERMINATED_STRING", "PEP_NEWLINE_IN_STRING",
               "PEP_INT_LITERAL_RANGE", "PEP_INVALID_UTF8")

FIXTURES = [
    ("nul_mid_string", b'say("a\\0b")\n'),
    ("crlf_positions", b"let a = 1\r\nlet b = @\r\n"),
    ("tab_positions", b"\tlet a = @\n"),
    ("utf8_4byte_unexpected", "\U0001F600".encode("utf-8")),
    ("utf8_ident_unexpected", "let caf\u00e9 = 1\n".encode("utf-8")),
    ("comment_after_program", b"fn main() -> Int { return 0 } # trailing"),
    ("comment_eof_no_newline", b"x # trailing"),
    ("bare_question", b"?"),
    ("unterminated_escape_eof", b'"abc\\'),
    ("unterminated_string", b'"abc'),
    ("newline_in_string", b'"a\nb"'),
    ("int_range", b"99999999999999999999"),
    ("invalid_utf8", b"let a = \x80;"),
    ("mixed_comment_hole", b'x _ = "s\\0" ?n # gone\n99'),
]

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_front_end(payload):
    with tempfile.TemporaryDirectory(prefix="a3-drv-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(payload)
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        parsed = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(f"seed check returned non-JSON (exit {done.returncode}): "
                           f"{done.stdout[:160]}{done.stderr[:160]}")
    diagnostics = parsed.get("diagnostics") or []
    first = diagnostics[0] if diagnostics else {}
    span = first.get("span") or {}
    start = span.get("start") or {}
    return {"status": parsed.get("status"),
            "code": first.get("code"),
            "offset": start.get("offset"),
            "end": span.get("endOffset"),
            "line": start.get("line"),
            "column": start.get("column")}


def lex_result_record(status, code, source_bytes, error_start, error_end, error_line,
                      error_column, tokens):
    return typed_record_value("LexResult", [
        ("status", typed("Str", status)),
        ("errorCode", typed("Str", code)),
        ("sourceBytes", typed("Int", str(source_bytes))),
        ("errorStart", typed("Int", str(error_start))),
        ("errorEnd", typed("Int", str(error_end))),
        ("errorLine", typed("Int", str(error_line))),
        ("errorColumn", typed("Int", str(error_column))),
        ("tokens", {"type": "List[LexToken]", "value": tokens}),
    ])


class Driver:
    def __init__(self):
        self.session = Session()
        opened = self.session.send({"schemaVersion": 3, "op": "open",
                                    "source": SCAN.read_text(encoding="utf-8") + PROBES,
                                    "name": "a3-driver-diff", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        self.document, self.revision = opened["document"], opened["revision"]
        sample = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": "a3-driver-vectors", "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        self.target_spec = {"document": sample["document"], "revision": sample["revision"],
                            "entryFunctions": []}
        eof = typed_record_value("LexToken", [
            ("kind", typed("Str", "eof")),
            ("text", typed("Str", "")),
            ("integerValue", typed("Int", "0")),
            ("stringParts", {"type": "List[Str]", "value": []}),
            ("startByte", typed("Int", "0")),
            ("endByte", typed("Int", "0")),
            ("line", typed("Int", "1")),
            ("column", typed("Int", "1")),
        ])
        registered = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                        "op": "tool_register", "tool": "a3-driver",
                                        "document": self.document,
                                        "revision": self.revision,
                                        "function": "a3_lex_probe"})
        require(registered, "status", "Registered", "register a3-driver")
        validated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_validate", "tool": "a3-driver",
                                       "document": self.document,
                                       "revision": self.revision,
                                       "testVectors": [{
                                           "arguments": [],
                                           "expect": lex_result_record("ok", "", 0, -1, -1, -1,
                                                                      -1, [eof]),
                                           "semanticTarget": self.target_spec}]})
        require(validated, "status", "Validated", "validate a3-driver")
        activated = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_activate", "tool": "a3-driver",
                                       "document": self.document,
                                       "revision": self.revision})
        require(activated, "status", "Active", "activate a3-driver")

    def lex(self, payload):
        target = self.session.send({"schemaVersion": 3, "op": "open_bytes",
                                    "name": f"a3-driver-{len(payload)}",
                                    "bytes": list(payload)})
        require(target, "outcome", "ok", "open payload")
        response = self.session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_invoke", "tool": "a3-driver",
                                      "arguments": [],
                                      "semanticTarget": {"document": target["document"],
                                                         "revision": target["revision"],
                                                         "entryFunctions": []}})
        require(response, "outcome", "ok", "invoke a3-driver (host refused the call)")
        fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
        tokens = []
        for item in fields["tokens"]["value"]:
            tok = {f["name"]: f["value"] for f in item["fields"]}
            tokens.append({"kind": tok["kind"]["value"],
                           "text": tok["text"]["value"],
                           "integerValue": int(tok["integerValue"]["value"]),
                           "stringParts": [p["value"] for p in tok["stringParts"]["value"]],
                           "startByte": int(tok["startByte"]["value"]),
                           "endByte": int(tok["endByte"]["value"]),
                           "line": int(tok["line"]["value"]),
                           "column": int(tok["column"]["value"])})
        return {"status": fields["status"]["value"],
                "errorCode": fields["errorCode"]["value"],
                "sourceBytes": int(fields["sourceBytes"]["value"]),
                "errorStart": int(fields["errorStart"]["value"]),
                "errorEnd": int(fields["errorEnd"]["value"]),
                "errorLine": int(fields["errorLine"]["value"]),
                "errorColumn": int(fields["errorColumn"]["value"]),
                "tokens": tokens}

    def close(self):
        self.session.close()


def main():
    print(f"REPO={REPO}")
    driver = Driver()
    try:
        errors, valids, positions, observations, later = [], [], [], [], []
        for name, payload in FIXTURES:
            seed = seed_front_end(payload)
            got = driver.lex(payload)
            rows = {"fixture": name, "seed": seed,
                    "driver": {k: v for k, v in got.items() if k != "tokens"},
                    "tokens": [(t["kind"], t["text"][:12], t["startByte"], t["endByte"],
                                t["line"], t["column"]) for t in got["tokens"]]}
            if seed["status"] == "incomplete":
                observations.append((name, seed, got))
                print(f"[O1 {name}] observation: seed=incomplete driver={got['status']} "
                      f"kinds={[t['kind'] for t in got['tokens']]}")
                continue
            if seed.get("code") in LEXER_CODES:
                if got["status"] != "error" or got["errorCode"] != seed["code"]:
                    errors.append(f"{name}: seed {seed['code']}@ {seed['offset']} vs driver "
                                  f"{got['status']}/{got['errorCode'] or '-'}@ "
                                  f"{got['errorStart']}")
                elif got["errorStart"] != seed["offset"]:
                    errors.append(f"{name}: same code {seed['code']} but driver offset "
                                  f"{got['errorStart']} != seed {seed['offset']}")
                if got["status"] == "error" and got["errorCode"] == seed["code"]:
                    if (got["errorLine"], got["errorColumn"]) != (seed["line"], seed["column"]):
                        positions.append(f"{name}: driver line/col "
                                         f"{got['errorLine']}:{got['errorColumn']} vs seed "
                                         f"{seed['line']}:{seed['column']}")
                print(f"[E1 {name}] seed={seed['code']}@{seed['offset']} "
                      f"({seed['line']}:{seed['column']}) driver={got['errorCode']}@"
                      f"{got['errorStart']} ({got['errorLine']}:{got['errorColumn']})")
            else:
                # The seed lexed the source; anything it reports now is parse/checker
                # level, so a driver error here would be a lexer disagreement.
                if seed["status"] == "valid" and (got["status"] != "ok" or got["errorCode"]):
                    valids.append(f"{name}: seed valid but driver "
                                  f"{got['status']}/{got['errorCode']}")
                elif seed["status"] != "valid" and got["status"] != "ok":
                    later.append(f"{name}: seed {seed['code']} but driver "
                                 f"{got['status']}/{got['errorCode']}")
                else:
                    valids.append(None)
                print(f"[E2/E4 {name}] seed={seed['status']}"
                      f"{('/' + seed['code']) if seed.get('code') else ''} "
                      f"driver={got['status']} kinds={[t['kind'] for t in got['tokens']]}")
        record("E1 error-code + offset parity with the seed", True,
               "parity", "parity" if not errors else "mismatch", "; ".join(errors))
        bad_valid = [item for item in valids if item]
        record("E2 valid-source parity", True, "parity",
               "parity" if not bad_valid else "mismatch", "; ".join(bad_valid))
        record("E4 later-stage-only refusals do not become driver errors", True,
               "driver ok", "driver ok" if not later else "mismatch", "; ".join(later))
        record("E3 position parity (line/column at the same byte offset)", True,
               "parity", "parity" if not positions else "mismatch", "; ".join(positions))
        RESULTS.append({"case": "O1 observations", "claimed": False, "expect": "observed",
                        "outcome": f"{len(observations)} incomplete-source fixtures",
                        "detail": json.dumps([o[0] for o in observations]),
                        "falsified": False})
    finally:
        driver.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['detail']}")
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
