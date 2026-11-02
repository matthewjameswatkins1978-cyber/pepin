"""Agent 3 TEMP measurement: A2 per-function-unit cost BASELINE at c70d5eb.

Lucy advisory (LUCY-20261102-006, item for A3): challenge A2's future
"no full re-run" claim with measured per-unit work. This pins the CURRENT
state, where A2's own receipt says each sectional/unit entry re-runs the
whole emission and then slices. If/when A2 lands a true bounded emit,
re-run this script: per-unit wall time must drop well below the one-shot
time for the claim to hold.

Measures, on the two-function fixture, 3 reps each (warm session):
  T_full   one-shot emit_c23_checked
  T_header section header
  T_unit0/1 function units
and verifies byte identity header + units + main == one-shot.
"""
import json
import pathlib
import sys
import time

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record  # noqa: E402

SOURCE = ("fn total(a: Int, b: Int) -> Int { return a + b }\n"
          "fn main() -> Int { return total(20, 22) }\n")
REPS = 3


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-unit-baseline", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]

        empty = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "e", "bytes": []})
        require(empty, "outcome", "ok", "open empty")
        target_spec = {"document": empty["document"], "revision": empty["revision"],
                       "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(empty["document"], empty["revision"])
        empty_checked = pep_c23.checker_report(empty["document"], empty["revision"])
        start_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"])
        finished_cursor = pep_c23.parser_cursor_value(empty["document"], empty["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        unsupported = typed_record("unsupported", (),
                                   "Pep C23 emission requires a top-level function named main")
        for tool, function, arguments, expected in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(empty["document"], empty["revision"], finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
                ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], unsupported),
                ("pep-c23-section", "emit_c23_section",
                 [empty_parsed, empty_checked, typed("Str", "header")], unsupported),
                ("pep-c23-function-unit", "emit_c23_function_unit",
                 [empty_parsed, empty_checked, typed("Int", 0)], unsupported)]:
            reg = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_register", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "function": function})
            require(reg, "status", "Registered", f"register {tool}")
            val = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_validate", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "testVectors": [{"arguments": arguments, "expect": expected,
                                                 "semanticTarget": target_spec}]})
            require(val, "status", "Validated", f"validate {tool}")
            act = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_activate", "tool": tool,
                                "document": tool_document, "revision": tool_revision})
            require(act, "status", "Active", f"activate {tool}")

        source_bytes = SOURCE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "target", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open target")
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        parsed = pep_c23.parse_target(session, source_bytes, target, tool_revision)
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic_target})
        require(checked, "outcome", "ok", "check target")
        checked_value = checked["result"]

        def emit(tool, arguments):
            started = time.perf_counter()
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": tool,
                                     "arguments": arguments, "semanticTarget": semantic_target})
            elapsed = time.perf_counter() - started
            require(response, "outcome", "ok", f"invoke {tool}")
            fields = {item["name"]: item["value"] for item in response["result"]["fields"]}
            assert fields["status"]["value"] == "emitted", fields["diagnostic"]["value"]
            text = "".join(p["value"] for p in fields["sourceParts"]["value"])
            return elapsed, text

        results = {}
        for rep in range(REPS):
            t, one = emit("pep-c23-emitter", [parsed, checked_value])
            results.setdefault("T_full", []).append(round(t * 1000, 1))
            t, header = emit("pep-c23-section", [parsed, checked_value, typed("Str", "header")])
            results.setdefault("T_header", []).append(round(t * 1000, 1))
            t, main_part = emit("pep-c23-section", [parsed, checked_value, typed("Str", "main")])
            results.setdefault("T_main", []).append(round(t * 1000, 1))
            units = []
            for index in (0, 1):
                t, unit = emit("pep-c23-function-unit",
                               [parsed, checked_value, typed("Int", index)])
                results.setdefault(f"T_unit{index}", []).append(round(t * 1000, 1))
                units.append(unit)
            if rep == 0:
                results["bytes"] = {"full": len(one), "header": len(header),
                                    "main": len(main_part),
                                    "unit0": len(units[0]), "unit1": len(units[1])}
                results["byte_identity"] = (header + units[0] + units[1] + main_part) == one

        summary = {key: (min(val), sum(val) / len(val)) if isinstance(val, list) else val
                   for key, val in results.items()}
        print(f"REPO={REPO}")
        print(json.dumps({"per_call_ms_min_avg": summary}, indent=2, sort_keys=True))
        full_avg = sum(results["T_full"]) / len(results["T_full"])
        unit0_avg = sum(results["T_unit0"]) / len(results["T_unit0"])
        verdict = ("unit_cost≈full_cost (full re-run corroborated)"
                   if unit0_avg >= 0.7 * full_avg else "unit_cost<full_cost (bounded emit progress)")
        print(f"RATIO unit0/full = {unit0_avg / full_avg:.2f} -> {verdict}")
        print(f"SUMMARY byte_identity={results['byte_identity']} reps={REPS}")
        return 0
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
