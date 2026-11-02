"""Measure the bounded-emitter claim: does a function-unit request cost O(unit) or O(program)?

Registers the Pep C23 emitter's three entry points as tools against the real compiler
bundle, then for programs of N trivial functions reports, per entry point, bytes, wall
time and outcome. Two facts matter:

  * byte identity -- header + every unit + main must equal the one-shot output;
  * scaling -- a unit request that stays flat as N grows is bounded; one that tracks the
    one-shot time is slice-after-emission.

A large-N case is included where whole-program emission should exhaust the fixed step
budget: an entry point that still succeeds there is genuinely bounded.

    python _build/probe_sections.py [--sizes 2,4,8,16,32]
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pep_c23
from pep_c23 import Session, require, parse_target, typed, typed_record


def make_program(count):
    """`count` trivial zero-argument functions plus main, all returning Int."""
    parts = [f"fn helper_{index}() -> Int {{ return {index} }}" for index in range(count)]
    parts.append("fn main() -> Int { return 0 }")
    return ("\n".join(parts) + "\n").encode("utf-8")


def parts_of(response):
    fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
    status = fields["status"]["value"]
    if status != "emitted":
        return status, fields["diagnostic"]["value"], None
    return status, fields["diagnostic"]["value"], [part["value"] for part in fields["sourceParts"]["value"]]


def register(session, tool_document, tool_revision, sample_document, sample_revision):
    target_spec = {"document": sample_document, "revision": sample_revision, "entryFunctions": []}
    empty_parsed = pep_c23.parser_progress(sample_document, sample_revision)
    empty_checked = pep_c23.checker_report(sample_document, sample_revision)
    expected = typed_record("unsupported", (), "Pep C23 emission requires a top-level function named main")
    start_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision)
    finished_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision,
                                                 done=True, lex_done=True, lex_stage="done")
    tools = [
        ("pep-c23-parser-start", "parser_start", [], start_cursor),
        ("pep-c23-parser-step", "parser_step", [finished_cursor],
         pep_c23.parser_chunk_value(sample_document, sample_revision, finished_cursor)),
        ("pep-c23-checker", "analyze_parsed", [empty_parsed], typed_checked(empty_checked)),
        ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], expected),
        ("pep-c23-section", "emit_c23_section", [empty_parsed, empty_checked, typed("Str", "header")], expected),
        ("pep-c23-unit", "emit_c23_function_unit", [empty_parsed, empty_checked, typed("Int", 0)], expected),
    ]
    for tool, function, arguments, expect in tools:
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                                   "tool": tool, "document": tool_document,
                                   "revision": tool_revision, "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_validate",
                                  "tool": tool, "document": tool_document, "revision": tool_revision,
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                                  "tool": tool, "document": tool_document, "revision": tool_revision})
        require(activated, "status", "Active", f"activate {tool}")


def typed_checked(report):
    """The checker report as the host sends it back to us (tool result encoding)."""
    return report


def invoke(session, tool, arguments, semantic_target):
    started = time.perf_counter()
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                             "tool": tool, "arguments": arguments, "semanticTarget": semantic_target})
    elapsed = (time.perf_counter() - started) * 1000.0
    if response.get("outcome") != "ok":
        return {"outcome": response.get("outcome"), "error": response.get("error", {}).get("code"), "ms": elapsed}
    return {"outcome": "ok", "ms": elapsed, "response": response}


def measure(session, tool_document, tool_revision, count):
    source = make_program(count)
    target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": f"n{count}", "bytes": list(source)})
    require(target, "outcome", "ok", "open target")
    semantic_target = {"document": target["document"], "revision": target["revision"], "entryFunctions": []}
    parsed = parse_target(session, source, target, tool_revision)
    checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                            "tool": "pep-c23-checker", "arguments": [parsed],
                            "semanticTarget": semantic_target})
    require(checked, "outcome", "ok", "check target")
    checked_value = checked["result"]
    row = {"functions": count}
    whole_parts = None

    whole = invoke(session, "pep-c23-emitter", [parsed, checked_value], semantic_target)
    if whole["outcome"] != "ok":
        row["all"] = {"outcome": whole["outcome"], "error": whole.get("error"), "ms": round(whole["ms"], 1)}
    else:
        status, diagnostic, parts = parts_of(whole["response"])
        row["all"] = {"status": status, "bytes": sum(len(part) for part in parts or []),
                      "parts": len(parts or []), "ms": round(whole["ms"], 1)}
        whole_parts = parts

    header = invoke(session, "pep-c23-section", [parsed, checked_value, typed("Str", "header")], semantic_target)
    epilogue = invoke(session, "pep-c23-section", [parsed, checked_value, typed("Str", "main")], semantic_target)
    for label, result in (("header", header), ("main", epilogue)):
        if result["outcome"] != "ok":
            row[label] = {"outcome": result["outcome"], "error": result.get("error"), "ms": round(result["ms"], 1)}
        else:
            status, _diagnostic, parts = parts_of(result["response"])
            row[label] = {"status": status, "bytes": sum(len(part) for part in parts or []),
                          "ms": round(result["ms"], 1)}

    units = []
    unit_ok = True
    for index in range(count + 1):
        result = invoke(session, "pep-c23-unit", [parsed, checked_value, typed("Int", index)], semantic_target)
        if result["outcome"] != "ok":
            units.append({"index": index, "outcome": result["outcome"], "error": result.get("error"),
                          "ms": round(result["ms"], 1)})
            unit_ok = False
            continue
        status, diagnostic, parts = parts_of(result["response"])
        units.append({"index": index, "status": status, "diagnostic": diagnostic,
                      "bytes": sum(len(part) for part in parts or []), "ms": round(result["ms"], 1)})
    row["unit_first"] = units[0]
    row["unit_last"] = units[-1]
    row["unit_calls"] = len(units)

    if whole_parts is not None and unit_ok and row.get("header", {}).get("status") == "emitted" \
            and row.get("main", {}).get("status") == "emitted":
        header_parts = parts_of(header["response"])[2]
        epilogue_parts = parts_of(epilogue["response"])[2]
        rebuilt = []
        rebuilt.extend(header_parts)
        for index in range(count + 1):
            result = invoke(session, "pep-c23-unit", [parsed, checked_value, typed("Int", index)], semantic_target)
            rebuilt.extend(parts_of(result["response"])[2])
        rebuilt.extend(epilogue_parts)
        row["byte_identity"] = "match" if rebuilt == whole_parts else "MISMATCH"
    else:
        row["byte_identity"] = "not-checked"
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="2,4,8,16,32")
    arguments = parser.parse_args()
    sizes = [int(item) for item in arguments.sizes.split(",") if item.strip()]

    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "stage-validation", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        register(session, tool_document, tool_revision, sample["document"], sample["revision"])
        for count in sizes:
            row = measure(session, tool_document, tool_revision, count)
            print(row, flush=True)
    finally:
        session.close()


if __name__ == "__main__":
    main()
