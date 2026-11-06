"""Pinned integration probe: report the checker stage and the emitter stage separately.

The discriminating bounded-emission case (a chunk holding `LexToken` and `make_token`) cannot be
judged from one number. If it fails, the question is always "checker or emitter?", and a single
`PEP_RUNTIME_STEP_LIMIT` hides which. This probe runs each stage as its own tool invocation and
labels the outcome, so a budget failure names its stage and a refusal names its diagnostic.

It is deliberately host-side: it drives the real `pep_c23` session, the real emitter bundle and the
real step limit. Nothing here is a model of the emitter.

    python tests/probe_integration_case.py --case all
    python tests/probe_integration_case.py --case lexer-chunk --json
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed, typed_record  # noqa: E402

LEXER = ROOT / "examples" / "pep_lexer.pep"

REGRESSION_FIXTURE = (
    "fn ascii_digit(byte: Int) -> Bool {\n"
    "  return 97 <= byte && byte <= 122 || byte == 95 || byte == 58 || byte == 44 || byte == 40 \n"
    "}\n\n"
    "fn ascii_continue(byte: Int) -> Bool {\n"
    "  return byte == 102 || byte == 95 || ascii_digit(byte)\n"
    "}\n\n"
    "fn has_next_identifier_byte(source: SourceBytes, offset: Int) -> Bool {\n"
    "  let length = byte_length(source)\n"
    "  return !(length <= offset) && ascii_continue(byte_at(source, offset))\n"
    "}\n"
    "fn main() -> Int { return 0 }\n")


def lexer_chunk():
    """`type LexToken` plus `make_token`, extracted by source span, not by rewriting."""
    lines = LEXER.read_text(encoding="utf-8").split("\n")
    declaration = "\n".join(lines[2:12])          # lines 3-12: type LexToken { ... }
    function = "\n".join(lines[112:122])           # lines 113-122: fn make_token(...) -> LexToken
    return declaration + "\n" + function + "\n"


def synthetic(count):
    functions = "\n".join(f"fn helper_{index}() -> Int {{ return {index} }}" for index in range(count))
    return functions + "\nfn main() -> Int { return 0 }\n"


# K4 (A4 spec/agent4-spec-lab@c25fab6, docs/spec/K4-STDLIB-PRIMITIVE.md): the one
# primitive gap A4 identified -- a function RETURNING a record. P1 is the L3
# `advance_position` shape verbatim from examples/pep_lexer.pep:90 (conditional
# returns of a record literal, Int-only fields). P2 is the L4 `make_token` shape
# with one wrong field type, which must refuse rather than launder.
# NOTE: A4's doc writes the record type without commas; the real source syntax
# (pep_lexer.pep:1) uses them, so these fixtures follow the source, not the doc.
K4_RECORD_RETURN = (
    "type SourcePosition { line: Int, column: Int }\n"
    "fn advance_position(line: Int, column: Int, byte: Int) -> SourcePosition {\n"
    "  if byte == 10 { return SourcePosition { line: line + 1, column: 1 } } else {\n"
    "    return SourcePosition { line: line, column: column + 1 }\n"
    "  }\n"
    "}\n"
    "fn main() -> Int {\n"
    "  let p = advance_position(1, 1, 10)\n"
    "  return p.line * 10 + p.column\n"
    "}\n")

K4_RECORD_MISMATCH = (
    "type LexToken { kind: Str, text: Str, line: Int, column: Int }\n"
    "fn make_token(kind: Str, text: Str, line: Int, column: Int) -> LexToken {\n"
    "  return LexToken { kind: kind, text: 0, line: line, column: column }\n"
    "}\n"
    "fn main() -> Int { return 0 }\n")

# SourceBytes ingress (dispatch: "inspect the next essential lexer SourceBytes native
# grant/byte access under checked target identity"). SB_PARAM is the shape the real
# lexer's scan_*_at helpers use: a SourceBytes parameter read through byte_length and
# byte_at, including a while loop with a byte_at initializer. SB_GRANT asks the
# separate question: can a native program OBTAIN a SourceBytes at all?
SB_PARAM = (
    "fn first_byte(source: SourceBytes) -> Int {\n"
    "  if byte_length(source) == 0 { return -1 } else {}\n"
    "  return byte_at(source, 0)\n"
    "}\n"
    "fn main() -> Int { return 0 }\n")

SB_GRANT = (
    "fn main() -> Int {\n"
    "  let source = source_bytes()\n"
    "  return byte_length(source)\n"
    "}\n")

# L6 control flow (the residual A4's K4 card named after record returns closed).
#
# RECURSION: the closure plan says "measure recursion, not assume it's unsupported at
# current head". Measured: it is refused, but NOT because it is recursion -- see the
# COMPUTED_ARG_* pair below, which isolates the actual trigger.
#
# WHILE_BYTE: while + `var` + assignment over a SourceBytes parameter. NOTE `<` is not
# a Pep operator at all (`PEP_UNEXPECTED_CHARACTER`); the language has `<=`, `==`,
# `!=`, `&&`, `||`, `!`. The real lexer writes `while !(a <= b)`, and so does this.
RECURSION = (
    "fn countdown(n: Int) -> Int {\n"
    "  if n <= 0 { return 0 } else {}\n"
    "  return countdown(n - 1) + 1\n"
    "}\n"
    "fn main() -> Int { return countdown(3) }\n")

WHILE_BYTE = (
    "fn count_bytes(source: SourceBytes) -> Int {\n"
    "  var offset = 0\n"
    "  while !(byte_length(source) <= offset) {\n"
    "    offset = offset + 1\n"
    "  }\n"
    "  return offset\n"
    "}\n"
    "fn main() -> Int { return 0 }\n")

# The discriminating pair. Same callee, same computed argument shape; the ONLY
# difference is whether the call site is in `main` or in an ordinary function.
# main: emitted. ordinary function: refused. So the recursion blocker is not
# recursion -- it is computed call arguments from non-main functions.
COMPUTED_ARG_MAIN = (
    "fn f(n: Int) -> Int { return n }\n"
    "fn main() -> Int { return f(1 - 1) }\n")

COMPUTED_ARG_NONMAIN = (
    "fn f(n: Int) -> Int { return n }\n"
    "fn g(n: Int) -> Int {\n"
    "  if n <= 0 { return 0 } else {}\n"
    "  return f(n - 1) + 1\n"
    "}\n"
    "fn main() -> Int { return g(1) }\n")

# Isolates the recursion refusal: is it recursion, or is it a computed call argument?
# Same callee shape as the seam probe's add_one(41), but the argument is a binary
# expression instead of a literal.
CALL_ARG_EXPR = (
    "fn add_one(v: Int) -> Int { return v + 1 }\n"
    "fn main() -> Int { return add_one(20 + 21) }\n")

CASES = {
    "lexer-chunk": lexer_chunk,
    "regression": lambda: REGRESSION_FIXTURE,
    "synthetic-8": lambda: synthetic(8),
    "synthetic-12": lambda: synthetic(12),
    "k4-record-return": lambda: K4_RECORD_RETURN,
    "k4-record-mismatch": lambda: K4_RECORD_MISMATCH,
    "sb-param": lambda: SB_PARAM,
    "sb-grant": lambda: SB_GRANT,
    "recursion": lambda: RECURSION,
    "while-byte": lambda: WHILE_BYTE,
    "call-arg-expr": lambda: CALL_ARG_EXPR,
    "computed-arg-main": lambda: COMPUTED_ARG_MAIN,
    "computed-arg-nonmain": lambda: COMPUTED_ARG_NONMAIN,
}


def stage(response, label):
    """One stage outcome, labelled. A budget failure names the stage that ran out."""
    if response.get("outcome") != "ok":
        error = response.get("error") or {}
        return {"stage": label, "outcome": response.get("outcome"),
                "code": error.get("code"), "detail": (error.get("message") or "")[:120]}
    return {"stage": label, "outcome": "ok"}


def emission_summary(response, label):
    if response.get("outcome") != "ok":
        return stage(response, label)
    fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
    status = fields["status"]["value"]
    parts = [part["value"] for part in fields["sourceParts"]["value"]]
    return {"stage": label, "outcome": "ok", "status": status,
            "bytes": sum(len(part) for part in parts),
            "detail": (fields["diagnostic"]["value"] or "")[:120]}


def register(session, document, revision, sample_document, sample_revision):
    target_spec = {"document": sample_document, "revision": sample_revision, "entryFunctions": []}
    empty_parsed = pep_c23.parser_progress(sample_document, sample_revision)
    empty_checked = pep_c23.checker_report(sample_document, sample_revision)
    refused = typed_record("unsupported", (), "Pep C23 emission requires a top-level function named main")
    start_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision)
    finished_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision,
                                                  done=True, lex_done=True, lex_stage="done")
    tools = [
        ("pep-c23-parser-start", "parser_start", [], start_cursor),
        ("pep-c23-parser-step", "parser_step", [finished_cursor],
         pep_c23.parser_chunk_value(sample_document, sample_revision, finished_cursor)),
        ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
        ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], refused),
        ("pep-c23-unit", "emit_c23_function_unit",
         [empty_parsed, empty_checked, typed("Int", 0)], refused),
        ("pep-c23-declaration-unit", "emit_c23_declaration_unit",
         [empty_parsed, empty_checked, typed("Int", 0)],
         typed_record("unsupported", (),
                      "Pep C23 declaration unit requires a top-level declaration id")),
    ]
    for tool, function, arguments, expect in tools:
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                   "tool": tool, "document": document, "revision": revision,
                                   "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                                  "tool": tool, "document": document, "revision": revision,
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                  "tool": tool, "document": document, "revision": revision})
        require(activated, "status", "Active", f"activate {tool}")


def run_case(session, tool_revision, name):
    source = CASES[name]()
    payload = source.encode("utf-8")
    row = {"case": name, "source_bytes": len(payload)}
    target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": name, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        row["open"] = stage(target, "open")
        return row
    semantic = {"document": target["document"], "revision": target["revision"], "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, tool_revision)
    except Exception as error:  # noqa: BLE001
        row["parse"] = {"stage": "parse", "outcome": "error", "detail": str(error)[:120]}
        return row
    row["parse"] = {"stage": "parse", "outcome": "ok",
                    "nodes": session.parser_measurements.get("parser_node_count")}
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                            "tool": "pep-c23-checker", "arguments": [parsed], "semanticTarget": semantic})
    row["check"] = stage(checked, "check")
    if checked.get("outcome") != "ok":
        return row
    fields = {item["name"]: item["value"] for item in checked["result"]["fields"]}
    row["check"]["status"] = fields["status"]["value"]
    if fields["status"]["value"] != "valid":
        return row

    whole = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                          "tool": "pep-c23-emitter", "arguments": [parsed, checked["result"]],
                          "semanticTarget": semantic})
    row["emit_all"] = emission_summary(whole, "emit_all")
    unit = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                         "tool": "pep-c23-unit",
                         "arguments": [parsed, checked["result"], typed("Int", 0)],
                         "semanticTarget": semantic})
    row["emit_unit_0"] = emission_summary(unit, "emit_unit_0")
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="all", choices=sorted(CASES) + ["all"])
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()

    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        register(session, document, revision, sample["document"], sample["revision"])
        names = sorted(CASES) if arguments.case == "all" else [arguments.case]
        rows = [run_case(session, revision, name) for name in names]
    finally:
        session.close()

    if arguments.json:
        print(json.dumps(rows, indent=2))
        return
    print(f"compiler bundle sha256 {__import__('hashlib').sha256(bundle.encode()).hexdigest()}")
    for row in rows:
        check = row.get("check", {})
        verdict = check.get("code") or check.get("status") or check.get("outcome")
        unit = row.get("emit_unit_0", {})
        print(f"{row['case']:14s} bytes={row['source_bytes']:5d} "
              f"nodes={row.get('parse', {}).get('nodes')} check={verdict} "
              f"unit0={unit.get('status') or unit.get('code')} "
              f"all={row.get('emit_all', {}).get('status') or row.get('emit_all', {}).get('code')}")


if __name__ == "__main__":
    main()
