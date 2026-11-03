"""A2 lexer-driver token-stream invariants on real programs — re-derived from the bytes.

`a2_driver_vs_seed.py` compares the driver with the seed on adversarial single-token
inputs. This probe attacks the *composition* surface instead: a whole multi-token
source, where the risk is a span off by one, a token silently skipped, a comment
swallowing code, or positions drifting after CRLF/tabs. The oracle is not the seed
and not the canonical lexer — it is the source bytes themselves:

  C1  coverage: the token spans plus independently computed trivia (whitespace and
      `#`/`//` comments) partition the source exactly; no byte is unaccounted for.
  C2  span fidelity: identifier/symbol token text equals the source slice,
      integer tokens carry `int(slice)` in `integerValue`, `eof` sits at the end.
  C3  position fidelity: each token's line/column equals a position recomputed
      from the bytes (LF advances the line, every byte advances the column).
  C4  string fidelity: independently decoding the literal body (escapes, incl.
      `\\0`) reproduces the driver's parts exactly, NUL included.
  C5  ordering: spans strictly increase, never overlap, `eof` last.

Exit codes: 0 = all claims hold, 1 = a claim falsified, 2 = harness error.
Usage: python a2_driver_stream_invariants.py <a2-worktree-at-pin>
"""
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record_value  # noqa: E402

SCAN = REPO / "stdlib" / "scan.pep"

PROBES = """
fn a3_stream_probe() -> LexResult {
  return lex_source(source_bytes())
}
"""

SYNTHETIC = {
    "statement": b"let a = 1;\n",
    "crlf_tabs": b"let\tx = 2\r\nlet y = x;\r\n",
    "comments": b"# leading comment\nlet a = 1; # trailing\n// slash comment\nlet b = 2;\n",
    "strings": b'say("a\\0b"); say("q\\"q"); let z = "\\n";\n',
    "holes_and_ops": b"x ?y == 3 && _;\n",
}

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


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
                               "op": "tool_register", "tool": "a3-stream",
                               "document": document, "revision": revision,
                               "function": "a3_stream_probe"})
    require(registered, "status", "Registered", "register a3-stream")
    validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": "a3-stream",
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
    require(validated, "status", "Validated", "validate a3-stream")
    activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": "a3-stream",
                              "document": document, "revision": revision})
    require(activated, "status", "Active", "activate a3-stream")


def lex(session, payload):
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": f"a3-stream-{len(payload)}", "bytes": list(payload)})
    require(target, "outcome", "ok", "open payload")
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": "a3-stream", "arguments": [],
                             "semanticTarget": {"document": target["document"],
                                                "revision": target["revision"],
                                                "entryFunctions": []}})
    if response.get("outcome") != "ok":
        error = response.get("error") or {}
        return {"status": "error", "errorCode": error.get("code"),
                "sourceBytes": len(payload), "tokens": []}
    fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
    tokens = []
    for item in fields["tokens"]["value"]:
        tok = {f["name"]: f["value"] for f in item["fields"]}
        tokens.append({"kind": tok["kind"]["value"], "text": tok["text"]["value"],
                       "integerValue": int(tok["integerValue"]["value"]),
                       "stringParts": [p["value"] for p in tok["stringParts"]["value"]],
                       "startByte": int(tok["startByte"]["value"]),
                       "endByte": int(tok["endByte"]["value"]),
                       "line": int(tok["line"]["value"]),
                       "column": int(tok["column"]["value"])})
    return {"status": fields["status"]["value"],
            "errorCode": fields["errorCode"]["value"],
            "sourceBytes": int(fields["sourceBytes"]["value"]),
            "tokens": tokens}


def decode_literal(body: bytes):
    """Independent decode of a string literal's body: escapes plus raw bytes."""
    out = bytearray()
    index = 0
    escapes = {ord("n"): b"\n", ord("t"): b"\t", ord("r"): b"\r", ord("\\"): b"\\",
               ord('"'): b'"', ord("0"): b"\x00"}
    while index < len(body):
        byte = body[index]
        if byte == 0x5C:  # backslash
            if index + 1 >= len(body):
                raise ValueError("dangling escape")
            code = body[index + 1]
            if code not in escapes:
                raise ValueError(f"unsupported escape \\{chr(code)}")
            out.extend(escapes[code])
            index += 2
        else:
            out.append(byte)
            index += 1
    return bytes(out)


def walk_trivia(source: bytes):
    """Independently classify bytes as trivia (whitespace or comment) or code."""
    trivia = set()
    index = 0
    length = len(source)
    while index < length:
        byte = source[index]
        if byte in (32, 9, 10, 13):
            trivia.add(index)
            index += 1
        elif byte == 0x23 or (byte == 0x2F and index + 1 < length and source[index + 1] == 0x2F):
            while index < length and source[index] != 10:
                trivia.add(index)
                index += 1
        else:
            index += 1
    return trivia


def position_of(source: bytes, offset: int):
    line, column = 1, 1
    for index in range(offset):
        if source[index] == 10:
            line, column = line + 1, 1
        else:
            column += 1
    return line, column


def main():
    print(f"REPO={REPO}")
    fixtures = {}
    for path in sorted((REPO / "examples").glob("*.pep")):
        if path.stat().st_size <= 4096:          # bounded: driver input, not a parser budget test
            fixtures[f"example:{path.name}"] = path.read_bytes()
    fixtures.update(SYNTHETIC)

    session = Session()
    try:
        scan_source = SCAN.read_text(encoding="utf-8") + PROBES
        opened = session.send({"schemaVersion": 3, "op": "open", "source": scan_source,
                               "name": "a3-stream-scan", "metadataOnly": True})
        require(opened, "outcome", "ok", "open scan module")
        require(opened, "status", "valid", "check scan module")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        register(session, opened["document"], opened["revision"],
                 sample["document"], sample["revision"])

        coverage, fidelity, positions, strings, ordering = [], [], [], [], []
        over_budget = []
        for name, source in fixtures.items():
            result = lex(session, source)
            if result["status"] != "ok":
                if result["errorCode"] == "PEP_RUNTIME_STEP_LIMIT":
                    # Not a token-stream defect: the driver ran out of the fixed
                    # 100,000-step tool budget. Measured separately (see
                    # a2_driver_budget_ceiling.py) and recorded here as data.
                    over_budget.append({"fixture": name, "bytes": len(source),
                                        "code": result["errorCode"]})
                    print(f"[O-budget {name}] {len(source)} bytes -> "
                          f"{result['errorCode']}")
                    continue
                coverage.append(f"{name}: driver error {result['errorCode']} "
                                f"(fixture expected to lex)")
                continue
            tokens = result["tokens"]
            if result["sourceBytes"] != len(source):
                coverage.append(f"{name}: sourceBytes {result['sourceBytes']} != {len(source)}")

            covered = set()
            for token in tokens:
                start, end = token["startByte"], token["endByte"]
                if start < 0 or end > len(source) or start > end:
                    fidelity.append(f"{name}: {token['kind']} span {start}..{end} out of range")
                    continue
                covered.update(range(start, end))
                slice_ = source[start:end]
                if token["kind"] in ("identifier", "symbol"):
                    if token["text"] != slice_.decode("utf-8", "replace"):
                        fidelity.append(f"{name}: {token['kind']} text "
                                        f"{token['text']!r} != slice {slice_!r}")
                elif token["kind"] == "integer":
                    try:
                        expected_value = int(slice_)
                    except ValueError:
                        fidelity.append(f"{name}: integer slice {slice_!r} is not numeric")
                    else:
                        if token["integerValue"] != expected_value:
                            fidelity.append(f"{name}: integer {token['integerValue']} != "
                                            f"{expected_value} from {slice_!r}")
                elif token["kind"] == "string":
                    try:
                        decoded = decode_literal(slice_[1:-1])
                    except ValueError as error:
                        strings.append(f"{name}: independent decode failed: {error}")
                    else:
                        got = "".join(token["stringParts"]).encode("utf-8")
                        if got != decoded:
                            strings.append(f"{name}: parts {got!r} != decoded {decoded!r}")
                elif token["kind"] == "hole":
                    # `?name` carries the name without the marker; a bare `_` has no name.
                    if slice_[:1] == b"?":
                        expected_text = slice_[1:].decode("utf-8", "replace")
                        if token["text"] != expected_text:
                            fidelity.append(f"{name}: hole text {token['text']!r} != "
                                            f"{expected_text!r} from {slice_!r}")
                    elif slice_ == b"_":
                        if token["text"] != "":
                            fidelity.append(f"{name}: bare hole carries text "
                                            f"{token['text']!r}")
                    else:
                        fidelity.append(f"{name}: hole token over {slice_!r}")
                elif token["kind"] == "eof":
                    if start != len(source):
                        fidelity.append(f"{name}: eof at {start} != {len(source)}")
                else:
                    fidelity.append(f"{name}: unexpected token kind {token['kind']!r}")

                expected_line, expected_column = position_of(source, start)
                if (token["line"], token["column"]) != (expected_line, expected_column):
                    positions.append(f"{name}: {token['kind']} at {start} has "
                                     f"{token['line']}:{token['column']} != "
                                     f"{expected_line}:{expected_column}")

            trivia = walk_trivia(source)
            missing = [index for index in range(len(source))
                       if index not in covered and index not in trivia]
            if missing:
                snippet = source[max(0, missing[0] - 8):missing[0] + 8]
                coverage.append(f"{name}: {len(missing)} byte(s) neither token nor trivia, "
                                f"first at {missing[0]} near {snippet!r}")

            previous_end = 0
            for token in tokens:
                if token["startByte"] < previous_end:
                    ordering.append(f"{name}: {token['kind']} starts {token['startByte']} "
                                    f"before previous end {previous_end}")
                previous_end = max(previous_end, token["endByte"])
            if tokens and tokens[-1]["kind"] != "eof":
                ordering.append(f"{name}: last token is {tokens[-1]['kind']}, not eof")

        record("C1 coverage: token spans + trivia partition the source", True, "parity",
               "parity" if not coverage else "mismatch", "; ".join(coverage))
        record("C2 span fidelity: text/value slices and eof position", True, "parity",
               "parity" if not fidelity else "mismatch", "; ".join(fidelity))
        record("C3 position fidelity: recomputed line/column", True, "parity",
               "parity" if not positions else "mismatch", "; ".join(positions))
        record("C4 string fidelity: independent escape decode", True, "parity",
               "parity" if not strings else "mismatch", "; ".join(strings))
        record("C5 ordering: spans increase, eof last", True, "parity",
               "parity" if not ordering else "mismatch", "; ".join(ordering))
        RESULTS.append({"case": "O-budget fixtures the driver cannot tokenise", "claimed": False,
                        "expect": "observed",
                        "outcome": f"{len(over_budget)} fixture(s)",
                        "detail": str(over_budget), "falsified": False})
        print(f"\nfixtures={len(fixtures)}: {', '.join(sorted(fixtures))}")
    finally:
        session.close()

    print("\n" + "%s" % (RESULTS,))
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
