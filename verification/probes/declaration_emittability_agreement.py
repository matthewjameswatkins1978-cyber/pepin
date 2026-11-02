"""Agent 3 declaration-check vs REAL-emission agreement probe
(`codex/a2-bounded-emission@4c4c5e1` — A2's "emittability is answerable
without emitting" claim; their explicit ask: attack the classification where
it could disagree with real emission).

Fixtures all carry `main` so whole-program refusal can only come from
declaration support (not a missing entry point):

  CTRL   supported record (Point) — control.
  EMPTY  `type Empty { }` — A2's own hazard fixture.
  UNION_EMPTY   union whose PAYLOAD record is empty (their ask a).
  REC_UNION     record field naming a union (their ask b).
  MUTUAL        mutually recursive unions — whole emission refuses with
                "tagged union has an unsupported layout" (my measured CL2).
  ORDER         record declared before the record it nests — whole emission
                refuses with "preceding record declaration" (my measured CL3).

Claims:
  CR1 EMPTY: check `unsupported` with "empty records" AND whole refuses with
      the IDENTICAL diagnostic text (A2: "the same diagnostic text emission
      would use").
  CR2 CTRL: check `ok` AND whole `emitted`.
  CR3 AGREEMENT on every checker-valid fixture: check `ok` ⇒ whole `emitted`;
      check `unsupported` ⇒ whole `unsupported` with the identical diagnostic.
      Any classification/emission disagreement falsifies (the hazard A2's
      check exists to remove).

Observations: checker status/diagnostics per fixture; bounded-unit status
(the dangling-reference coexistence A2 pinned).

Pure checker/session emit layer; no native build, no execution.
Exit: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python declaration_emittability_agreement.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record  # noqa: E402

RESULTS = {}

FIXTURES = {
    "CTRL": ("type Point { x: Int y: Int }\n"
             "fn use_point(p: Point) -> Int { return p.x }\n"
             "fn main() -> Int { return 0 }\n"),
    "EMPTY": ("type Empty { }\n"
              "fn use_empty(e: Empty) -> Int { return 0 }\n"
              "fn main() -> Int { return 0 }\n"),
    "UNION_EMPTY": ("type E2 { }\n"
                    "type U = W(E2)\n"
                    "fn take(u: U) -> Int { return 0 }\n"
                    "fn main() -> Int { return 0 }\n"),
    # Nullary union variants REQUIRE `A2()` — bare `A2` parse-fails
    # `PEP_PARSE_EXPECTED: Expected '(` (measured; pinned grammar fact).
    "REC_UNION": ("type U2 = A2() | B2(Int)\n"
                  "type R { u: U2 }\n"
                  "fn take(r: R) -> Int { return 0 }\n"
                  "fn main() -> Int { return 0 }\n"),
    "MUTUAL": ("type Ping = WrapP(Pong)\n"
               "type Pong = WrapQ(Ping)\n"
               "fn take(p: Ping) -> Int { return 0 }\n"
               "fn main() -> Int { return 0 }\n"),
    "ORDER": ("fn take(o: Outer) -> Int { return o.i.x }\n"
              "type Outer { i: Inner }\n"
              "type Inner { x: Int }\n"
              "fn main() -> Int { return 0 }\n"),
}


def record(name, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS[name] = {"case": name, "claim_case": claim, "expect": expect,
                     "outcome": outcome, "detail": detail, "falsified": falsified}


def function_node_id(nodes, index=0):
    found = []
    for node in nodes:
        fields = {f["name"]: f["value"] for f in node["fields"]}
        if fields["kind"]["value"] == "function" and \
                str(fields["parentId"]["value"]) == "-1":
            found.append(int(fields["id"]["value"]))
    if index >= len(found):
        raise AssertionError(f"no top-level function at index {index}")
    return found[index]


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-decl-agree", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        tool_document, tool_revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "stage-validation", "bytes": []})
        require(sample, "outcome", "ok", "open sample")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_parsed = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        refused = typed_record("unsupported", (),
                               "Pep C23 emission requires a top-level function named main")
        refused_bounded = pep_c23.typed_record_value("PepC23BoundedUnit", [
            ("status", typed("Str", "unsupported")),
            ("diagnostic", typed("Str", "Pep C23 function unit index is out of range")),
            ("sourceParts", pep_c23.typed_list("Str")),
            ("prerequisiteKinds", pep_c23.typed_list("Str")),
            ("prerequisiteIds", pep_c23.typed_list("Int")),
            ("requiresArena", typed("Bool", False)),
        ])
        ok_declarations = pep_c23.typed_record_value("PepC23DeclarationCheck", [
            ("status", typed("Str", "ok")),
            ("diagnostic", typed("Str", "")),
        ])
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], refused),
            ("pep-c23-bounded-unit", "emit_c23_function_unit_bounded",
             [empty_parsed, empty_checked, typed("Int", 0)], refused_bounded),
            ("pep-c23-declarations-check", "pep_c23_unit_declarations_check",
             [pep_c23.typed_list("FlatAstNode", []), typed("Int", 0)], ok_declarations),
        ]
        for tool, function, arguments, expect in tools:
            reg = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_register", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "function": function})
            require(reg, "status", "Registered", f"register {tool}")
            val = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_validate", "tool": tool,
                                "document": tool_document, "revision": tool_revision,
                                "testVectors": [{"arguments": arguments, "expect": expect,
                                                 "semanticTarget": target_spec}]})
            require(val, "status", "Validated", f"validate {tool}")
            act = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_activate", "tool": tool,
                                "document": tool_document, "revision": tool_revision})
            require(act, "status", "Active", f"activate {tool}")

        per_fixture = {}
        for name, source in FIXTURES.items():
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": name, "bytes": list(payload)})
            require(target, "outcome", "ok", f"open {name}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            query = session.send({"schemaVersion": 3, "op": "query",
                                  "document": target["document"],
                                  "revision": target["revision"]})
            entry = {"checker": query.get("status"),
                     "checker_diags": [(d.get("code"), d.get("message"))
                                       for d in (query.get("diagnostics") or [])]}
            per_fixture[name] = entry
            if query.get("status") != "valid":
                entry["skipped"] = "checker-invalid (cannot reach emission)"
                continue
            parsed = pep_c23.parse_target(session, payload, target, tool_revision)
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": sem})
            require(checked, "outcome", "ok", f"check {name}")
            checked_value = checked["result"]

            fields = pep_c23.typed_fields(parsed, "ParserProgress", "parser progress")
            nodes = pep_c23.typed_field_value(fields, "nodes", "List[FlatAstNode]",
                                              "parser progress")
            check = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_invoke",
                                  "tool": "pep-c23-declarations-check",
                                  "arguments": [{"type": "List[FlatAstNode]", "value": nodes},
                                                typed("Int", function_node_id(nodes, 0))],
                                  "semanticTarget": sem})
            require(check, "outcome", "ok", f"decl check {name}")
            cfields = {f["name"]: f["value"] for f in check["result"]["fields"]}
            entry["check_status"] = cfields["status"]["value"]
            entry["check_diagnostic"] = cfields["diagnostic"]["value"]

            whole = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_invoke", "tool": "pep-c23-emitter",
                                  "arguments": [parsed, checked_value],
                                  "semanticTarget": sem})
            require(whole, "outcome", "ok", f"whole {name}")
            wfields = {f["name"]: f["value"] for f in whole["result"]["fields"]}
            entry["whole_status"] = wfields["status"]["value"]
            entry["whole_diagnostic"] = wfields["diagnostic"]["value"]

            unit = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-bounded-unit",
                                 "arguments": [parsed, checked_value, typed("Int", 0)],
                                 "semanticTarget": sem})
            ufields = {f["name"]: f["value"] for f in unit["result"]["fields"]}
            entry["unit_status"] = ufields["status"]["value"]

        # ---- claims ---------------------------------------------------------
        empty = per_fixture.get("EMPTY", {})
        if empty.get("check_status"):
            ok = (empty["check_status"] == "unsupported"
                  and "empty records" in empty["check_diagnostic"]
                  and empty["whole_status"] == "unsupported"
                  and empty["whole_diagnostic"] == empty["check_diagnostic"])
            record("CR1 EMPTY record: check unsupported AND whole refuses with the "
                   "IDENTICAL diagnostic text", True, "agree-identical-text",
                   "agree-identical-text" if ok else "mismatch",
                   json.dumps(empty))
        else:
            record("CR1 EMPTY record: check unsupported AND whole refuses with the "
                   "IDENTICAL diagnostic text", True, "agree-identical-text",
                   "unreachable", json.dumps(empty))

        ctrl = per_fixture.get("CTRL", {})
        if ctrl.get("check_status"):
            ok = ctrl["check_status"] == "ok" and ctrl["whole_status"] == "emitted"
            record("CR2 control record: check ok AND whole emitted", True, "ok-emitted",
                   "ok-emitted" if ok else "mismatch", json.dumps(ctrl))
        else:
            record("CR2 control record: check ok AND whole emitted", True, "ok-emitted",
                   "unreachable", json.dumps(ctrl))

        disagreements = {}
        for name in ("UNION_EMPTY", "REC_UNION", "MUTUAL", "ORDER"):
            entry = per_fixture.get(name, {})
            if not entry.get("check_status"):
                disagreements[name] = {"state": "checker-invalid",
                                       "diags": entry.get("checker_diags")}
                continue
            if entry["check_status"] == "ok":
                agree = entry["whole_status"] == "emitted"
                reason = None if agree else f"check ok but whole={entry['whole_status']}:" \
                         f" {entry['whole_diagnostic'][:100]}"
            else:
                agree = (entry["whole_status"] == "unsupported"
                         and entry["whole_diagnostic"] == entry["check_diagnostic"])
                reason = None if agree else (
                    f"check={entry['check_status']} whole={entry['whole_status']} "
                    f"text_equal={entry['whole_diagnostic'] == entry['check_diagnostic']}")
            if not agree:
                disagreements[name] = {"reason": reason, **entry}
        record("CR3 classification and real emission AGREE on every checker-valid "
               "fixture (no disagreement the hazard-check would miss)", True,
               "all-agree", "all-agree" if not disagreements else "disagreement",
               json.dumps(disagreements))

        # ---- observations ----------------------------------------------------
        record("O1 per-fixture map (checker / check / whole / unit)", False, "observed",
               json.dumps(per_fixture), "")
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    items = list(RESULTS.values())
    falsified = [i for i in items if i["falsified"]]
    print(f"REPO={REPO}")
    print(json.dumps(items, indent=2, sort_keys=True))
    print(f"SUMMARY cases={len(items)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']} ({item['detail']})")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # harness failure must NOT read as falsification
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
