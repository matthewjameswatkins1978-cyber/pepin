"""Agent 3 independent probe: the A1/A2 `make_token` reconciliation, measured.

Claim under attack (A2 commit `c70d5eb`, "feat(c23): bounded chunks need no
main ..."):

  R1  `LexToken` + `make_token` (NO main) is checker-valid on A1's checker —
      A1's "make_token valid" and A2's "make_token step-limit" were both
      correct about different shapes: it is cost, not rejection.

  R2 (observation, no claim): adding a `main` that calls the constructor is
      what exceeds the checker's step budget (A2 measured `budget exceeded at
      2428:3`). A2 did not commit that +main fixture, so this probe reconstructs
      a minimal caller; whatever happens is recorded verbatim as MY measurement
      of MY fixture, not an exact-fixture parity check.

Fixture: `type LexToken` + `fn make_token` extracted verbatim from
`examples/pep_lexer.pep` (same extraction rule as A2's test). Harness: staged
parser + checker tools only (no emitter, no native build, no execution).

Target pin: pass the pinned A1 worktree as argv[1].

Exit code: 0 = R1 observed as claimed, 1 = R1 falsified.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed_record  # noqa: E402

RESULTS = []
LEXER = REPO / "examples" / "pep_lexer.pep"

MAIN_CALLER = (
    "fn main() -> Int {\n"
    "  let parts: List[Str] = []\n"
    "  let token = make_token(\"id\", \"x\", 0, parts, 0, 1, 1, 1)\n"
    "  return token.startByte\n"
    "}\n"
)


def block(lexer_text, header):
    start = lexer_text.index("\n" + header) if ("\n" + header) in lexer_text \
        else lexer_text.index(header)
    if lexer_text[start] == "\n":
        start += 1
    depth = 0
    index = lexer_text.index("{", start)
    for position in range(index, len(lexer_text)):
        character = lexer_text[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return lexer_text[start:position + 1]
    raise AssertionError(header)


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def check(session, tool_document, tool_revision, name, source_text):
    """Run parse + check; return (kind, detail) where kind is the status or error code."""
    source_bytes = source_text.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": name,
                           "bytes": list(source_bytes)})
    require(target, "outcome", "ok", f"open {name}")
    semantic_target = {"document": target["document"], "revision": target["revision"],
                       "entryFunctions": []}
    try:
        parsed = pep_c23.parse_target(session, source_bytes, target, tool_revision)
    except RuntimeError as error:
        return "PARSE_ERROR", str(error)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker",
                            "arguments": [parsed], "semanticTarget": semantic_target})
    if checked.get("outcome") != "ok":
        error = checked.get("error") or {}
        return error.get("code", "UNKNOWN_ERROR"), json.dumps(error)
    fields = {item["name"]: item["value"] for item in checked["result"]["fields"]}
    return fields["status"]["value"], json.dumps(
        {k: fields[k] for k in ("status", "diagnostic") if k in fields})


def main():
    lexer_text = LEXER.read_text(encoding="utf-8")
    base = block(lexer_text, "type LexToken") + "\n" + block(lexer_text, "fn make_token") + "\n"
    with_caller = base + "\n" + MAIN_CALLER

    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-maketoken-recon", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]

        empty = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "e", "bytes": []})
        require(empty, "outcome", "ok", "open empty target")
        target_spec = {"document": empty["document"], "revision": empty["revision"],
                       "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(empty["document"], empty["revision"])
        empty_checked = pep_c23.checker_report(empty["document"], empty["revision"])
        start_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"])
        finished_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        for tool, function, arguments, expected in [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(empty["document"], empty["revision"], finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
        ]:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                       "op": "tool_register", "tool": tool,
                                       "document": tool_document, "revision": tool_revision,
                                       "function": function})
            require(registered, "status", "Registered", f"register {tool}")
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_document, "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments, "expect": expected,
                                                       "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_activate", "tool": tool,
                                      "document": tool_document, "revision": tool_revision})
            require(activated, "status", "Active", f"activate {tool}")

        kind, detail = check(session, tool_document, tool_revision, "no-main", base)
        record("R1 LexToken+make_token without main checks valid", True, "valid",
               kind, detail)

        kind, detail = check(session, tool_document, tool_revision, "with-caller", with_caller)
        record("R2 observation: + reconstructed main caller", False, "observed",
               kind, detail)
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(f"FIXTURE base=type LexToken + fn make_token (verbatim from examples/pep_lexer.pep); "
          f"caller=RECONSTRUCTED (A2 did not commit theirs)")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
