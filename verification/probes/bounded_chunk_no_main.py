"""Agent 3 independent probe: bounded chunk without `main` at A2 pin c70d5eb.

Claims under attack (A2-owned `codex/a2-list-record-fields@c70d5eb`, commit
"feat(c23): bounded chunks need no main; and a measured limit on slice-after
emission"):

  C1  The one-shot path (`emit_c23_checked`, part == all) STILL refuses a
      program with no `main`: the main guard was narrowed to whole-program and
      epilogue emission only, not removed.
  C2  On the SAME no-main source, section `header` emits (#include present).
  C3  Section `function` emits the function definition and no `int main(`.
  C5  Function unit 0 emits for the no-main source (a bounded chunk carrying
      one function and no main is legitimate).

C4 (section `main` on a no-main source) is recorded as an observation only.

The harness mirrors A2's own `tests/test_c23_section_identity.py` registration
sequence (read-only reuse of the builder's test scaffolding) because
`emit_c23_section`/`emit_c23_function_unit` are not host-registered entry
points. Pure emit layer: no native compilation, no execution of generated C.

Exit code: 0 = every claim case observed as claimed, 1 = a claim case falsified.

Usage: python bounded_chunk_no_main.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record  # noqa: E402

RESULTS = []
SOURCE = "fn add(a: Int, b: Int) -> Int { return a + b }\n"


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def fields_of(response):
    return {item["name"]: item["value"] for item in response["result"]["fields"]}


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-no-main-probe", "metadataOnly": True})
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
        unsupported = typed_record("unsupported", (),
                                   "Pep C23 emission requires a top-level function named main")
        registrations = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(empty["document"], empty["revision"], finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], unsupported),
            ("pep-c23-section", "emit_c23_section",
             [empty_parsed, empty_checked, typed("Str", "header")], unsupported),
            ("pep-c23-function-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], unsupported),
        ]
        for tool, function, arguments, expected in registrations:
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

        # --- the no-main target under test -------------------------------
        source_bytes = SOURCE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "no-main", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open no-main target")
        semantic_target = {"document": target["document"], "revision": target["revision"],
                           "entryFunctions": []}
        parsed = pep_c23.parse_target(session, source_bytes, target, tool_revision)
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic_target})
        if checked.get("outcome") != "ok":
            record("checker accepts no-main source", True, "checked",
                   "NOT_CHECKED", json.dumps(checked.get("error")))
            raise SystemExit(1)
        checked_value = checked["result"]

        def invoke(tool, arguments):
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": tool,
                                     "arguments": arguments, "semanticTarget": semantic_target})
            require(response, "outcome", "ok", f"invoke {tool}")
            return fields_of(response)

        # C1: one-shot still refuses no-main
        one_shot = invoke("pep-c23-emitter", [parsed, checked_value])
        one_status = one_shot["status"]["value"]
        one_diag = one_shot["diagnostic"]["value"]
        record("C1 one-shot part=all refuses no-main source",
               True, "unsupported",
               "unsupported" if one_status == "unsupported" else one_status,
               f"status={one_status} diagnostic={one_diag!r}")

        # C2: header section emits
        header = invoke("pep-c23-section", [parsed, checked_value, typed("Str", "header")])
        h_status = header["status"]["value"]
        h_text = "".join(p["value"] for p in header["sourceParts"]["value"])
        record("C2 section header emits for no-main source",
               True, "emitted+include",
               "emitted+include" if (h_status == "emitted" and "#include" in h_text)
               else h_status,
               f"status={h_status} bytes={len(h_text)}")

        # C3: function section emits the definition, no int main(
        body = invoke("pep-c23-section", [parsed, checked_value, typed("Str", "function")])
        b_status = body["status"]["value"]
        b_text = "".join(p["value"] for p in body["sourceParts"]["value"])
        ok = (b_status == "emitted" and "int64_t pep_fn_" in b_text
              and "int main(" not in b_text)
        record("C3 section function emits definition without int main(",
               True, "emitted+defn",
               "emitted+defn" if ok else b_status,
               f"status={b_status} pep_fn={'int64_t pep_fn_' in b_text} "
               f"int_main={'int main(' in b_text}")

        # C4 (observation, no claim): main section on a no-main source
        epilogue = invoke("pep-c23-section", [parsed, checked_value, typed("Str", "main")])
        e_status = epilogue["status"]["value"]
        e_text = "".join(p["value"] for p in epilogue["sourceParts"]["value"])
        record("C4 observation: section main on no-main source", False, "observed",
               e_status, f"status={e_status} bytes={len(e_text)} "
                         f"diagnostic={epilogue['diagnostic']['value']!r}")

        # C5: function unit 0 emits for the no-main source
        unit = invoke("pep-c23-function-unit", [parsed, checked_value, typed("Int", 0)])
        u_status = unit["status"]["value"]
        u_text = "".join(p["value"] for p in unit["sourceParts"]["value"])
        ok = (u_status == "emitted" and "int64_t pep_fn_" in u_text
              and "int main(" not in u_text)
        record("C5 function unit 0 emits for no-main source",
               True, "emitted+defn",
               "emitted+defn" if ok else u_status,
               f"status={u_status} bytes={len(u_text)}")
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(RESULTS, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    sys.exit(main())
