"""Recheck A1's "flip 66n regression" claim at a fix pin, using the candidate's
own stage-probe fixture — without running the frozen Full.

Why this exists: the frozen runner derives the `discriminating rows` gate from
`tests/probe_integration_case.py --case all` in the candidate tree, and that row
(`regression … check=<valid|CODE>`) is exactly what A1 claims to have flipped at
`e36e67d`/`ba4b057`. The frozen probe file does not exist on the fix branch, so
this instrument re-uses its **fixture text verbatim** (copied from
`tests/probe_integration_case.py` REGRESSION_FIXTURE at `8396b63`, unchanged) and
runs only the two stages that decide the row: the Pep-written parser, then the
Pep-written checker. No emitter, no native build, no frozen gate executed.

Output line is deliberately shaped like the runner's own row so it can be
compared across pins:

  regression bytes=<n> nodes=<n> check=<valid|PEP_RUNTIME_STEP_LIMIT|...>

Exit codes: 0 = the row reports `check=valid` (flipped), 1 = it does not
(the row would still fail the frozen gate), 2 = harness error.

Usage: python regression_row_recheck.py <pinned-worktree>
"""
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require, typed, typed_record  # noqa: E402

# Verbatim from tests/probe_integration_case.py (8396b63) — the `regression` row
# fixture. Nothing here rewrites it; a change would invalidate the comparison.
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


def register(session, document, revision, sample_document, sample_revision):
    target_spec = {"document": sample_document, "revision": sample_revision,
                   "entryFunctions": []}
    empty_parsed = pep_c23.parser_progress(sample_document, sample_revision)
    empty_checked = pep_c23.checker_report(sample_document, sample_revision)
    refused = typed_record("unsupported", (),
                           "Pep C23 emission requires a top-level function named main")
    start_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision)
    finished_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision,
                                                  done=True, lex_done=True, lex_stage="done")
    tools = [
        ("pep-c23-parser-start", "parser_start", [], start_cursor),
        ("pep-c23-parser-step", "parser_step", [finished_cursor],
         pep_c23.parser_chunk_value(sample_document, sample_revision, finished_cursor)),
        ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
    ]
    for tool, function, arguments, expect in tools:
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_register", "tool": tool,
                                   "document": document, "revision": revision,
                                   "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": document, "revision": revision,
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": tool,
                                  "document": document, "revision": revision})
        require(activated, "status", "Active", f"activate {tool}")
    # keep the unused `refused` vector referenced so the intent stays visible
    _ = refused


def main():
    source_bytes = REGRESSION_FIXTURE.encode("utf-8")
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-regression-row", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "a3-regression-vectors", "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        register(session, opened["document"], opened["revision"],
                 sample["document"], sample["revision"])

        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "a3-regression-target", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open regression fixture")
        semantic_target = {"document": target["document"],
                           "revision": target["revision"], "entryFunctions": []}
        parsed = parse_target(session, source_bytes, target, opened["revision"])
        nodes = len({field["name"]: field["value"] for field in parsed["fields"]}["nodes"]["value"])
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic_target})
        if checked.get("outcome") != "ok":
            error = checked.get("error") or {}
            check = error.get("code") or "NO_CODE"
            print(f"checker_refusal_code={check} message={str(error.get('message'))[:200]}")
        else:
            fields = {item["name"]: item["value"] for item in checked["result"]["fields"]}
            check = fields["status"]["value"]
    finally:
        session.close()

    print(f"REPO={REPO}")
    print(f"regression bytes={len(source_bytes)} nodes={nodes} check={check}")
    if check == "valid":
        print("VERDICT flipped: the discriminating regression row reports check=valid")
        return 0
    print(f"VERDICT not flipped: check={check}")
    return 1


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
