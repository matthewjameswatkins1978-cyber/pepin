"""Agent 3 closure-attack probe for A2's prerequisite closure
(`codex/a2-bounded-emission@cbdce20`, slice 4 `09cd8f7`) — the three attacks
A2 asked for on #16, plus the assignment's transitive-prerequisite themes.

  CL1 SELF-REFERENTIAL UNION — `type Expr = Number(Int) | Add(Expr, Expr)`.
      Claim: the bounded unit for a function taking `Expr` returns (closure
      terminates) and, if emitted, its prerequisite ids are EXACTLY the union
      declaration itself (self-reference deduplicated, nothing invented).
  CL2 MUTUALLY RECURSIVE UNIONS — `Ping` wraps `Pong`, `Pong` wraps `Ping`.
      Claim: terminates; if emitted, prerequisite ids are EXACTLY {Ping, Pong}.
      (If the checker refuses mutual recursion first, that is recorded as an
      observation — the closure stays unreachable through a valid pipeline.)
  CL3 TYPE DECLARED AFTER ITS USE inside prerequisite expansion — `fn take`
      first, then `Outer { i: Inner }`, then `Inner`. Claim: refuses with a
      diagnostic OR reports BOTH declarations — an emitted unit whose
      prerequisite set omits `Inner` falsifies "refused, not omitted".
  CL4 DECLARATION WHOSE FIELD REFERENCES AN UNDECLARED NAME — claim: refused
      at some stage (checker or closure), never silently omitted; if both
      stages accept and the unit emits without the reference resolved, that
      falsifies the claim.

Observations: per-fixture checker status/diagnostics, whole-emission status,
unit status/diagnostics (vacuity and stage attribution).

Pure checker/session emit layer: no native build, no execution.
Exit: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python prereq_closure_attacks.py <repo-root-at-pin>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record  # noqa: E402

RESULTS = []

SELF_UNION = ("type Expr = Number(Int) | Add(Expr, Expr)\n"
              "fn count(e: Expr) -> Int { return 0 }\n"
              "fn main() -> Int { return count(Number(1)) }\n")
# main deliberately CONSTRUCTS nothing: pure mutual unions have no base
# case, and my first main (`take(WrapQ(WrapP(1)))`) was a type error of
# mine (`Expected Pong but found Int`), not the compiler's — disclosed.
MUTUAL_UNIONS = ("type Ping = WrapP(Pong)\n"
                 "type Pong = WrapQ(Ping)\n"
                 "fn take(p: Ping) -> Int { return 0 }\n"
                 "fn main() -> Int { return 0 }\n")
FORWARD_IN_PREREQ = ("fn take(o: Outer) -> Int { return o.i.x }\n"
                     "type Outer { i: Inner }\n"
                     "type Inner { x: Int }\n"
                     "fn main() -> Int { return 0 }\n")
UNDECLARED_FIELD = ("type Outer { i: Nope }\n"
                    "fn take(o: Outer) -> Int { return 0 }\n"
                    "fn main() -> Int { return 0 }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-closure-attacks", "metadataOnly": True})
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
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                      done=True, lex_done=True, lex_stage="done")
        refused_bounded = pep_c23.typed_record_value("PepC23BoundedUnit", [
            ("status", typed("Str", "unsupported")),
            ("diagnostic", typed("Str", "Pep C23 function unit index is out of range")),
            ("sourceParts", pep_c23.typed_list("Str")),
            ("prerequisiteKinds", pep_c23.typed_list("Str")),
            ("prerequisiteIds", pep_c23.typed_list("Int")),
            ("requiresArena", typed("Bool", False)),
        ])
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker", "analyze_parsed", [empty_parsed], empty_checked),
            ("pep-c23-emitter", "emit_c23_checked", [empty_parsed, empty_checked], refused),
            ("pep-c23-bounded-unit", "emit_c23_function_unit_bounded",
             [empty_parsed, empty_checked, typed("Int", 0)], refused_bounded),
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

        def top_level_ids_and_kinds(parsed):
            nodes = next(f for f in parsed["fields"] if f["name"] == "nodes")
            out = []
            for node in nodes["value"]["value"]:
                fields = {f["name"]: f["value"] for f in node["fields"]}
                if str(fields["parentId"]["value"]) == "-1":
                    out.append((int(fields["id"]["value"]), fields["kind"]["value"],
                                fields["text"]["value"]))
            return out

        def run_fixture(name, source, unit_index, expect_ids):
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": name, "bytes": list(payload)})
            require(target, "outcome", "ok", f"open {name}")
            semantic = {"document": target["document"], "revision": target["revision"],
                        "entryFunctions": []}
            query = session.send({"schemaVersion": 3, "op": "query",
                                  "document": target["document"],
                                  "revision": target["revision"]})
            check_status = query.get("status")
            check_diags = [(d.get("code"), d.get("message"))
                           for d in (query.get("diagnostics") or [])]
            if check_status != "valid":
                record(f"{name}: fixture stage map", False, "observed",
                       "checker-invalid",
                       json.dumps({"check_status": check_status, "diags": check_diags}))
                return {"stage": "checker-invalid", "diags": check_diags}
            try:
                parsed = pep_c23.parse_target(session, payload, target, tool_revision)
            except Exception as error:  # noqa: BLE001
                record(f"{name}: fixture stage map", False, "observed", "parse-error",
                       f"{type(error).__name__}: {error}")
                return {"stage": "parse-error"}
            tops = top_level_ids_and_kinds(parsed)
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": semantic})
            if checked.get("outcome") != "ok":
                record(f"{name}: fixture stage map", False, "observed", "tool-error",
                       json.dumps(checked.get("error"))[:200])
                return {"stage": "tool-error"}

            def bounded_at(index):
                response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke",
                                         "tool": "pep-c23-bounded-unit",
                                         "arguments": [parsed, checked["result"],
                                                       typed("Int", index)],
                                         "semanticTarget": semantic})
                if response.get("outcome") != "ok":
                    return {"status": "INVOKE_ERROR",
                            "diagnostic": json.dumps(response.get("error"))[:200],
                            "ids": [], "kinds": []}
                fields = {f["name"]: f["value"] for f in response["result"]["fields"]}
                return {"status": fields["status"]["value"],
                        "diagnostic": fields["diagnostic"]["value"],
                        "ids": [int(i["value"])
                                for i in fields["prerequisiteIds"]["value"]],
                        "kinds": [k["value"]
                                  for k in fields["prerequisiteKinds"]["value"]]}

            unit = bounded_at(unit_index)
            # whole-program status for stage attribution (observation only)
            whole = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_invoke", "tool": "pep-c23-emitter",
                                  "arguments": [parsed, checked["result"]],
                                  "semanticTarget": semantic})
            whole_status, whole_diag = "INVOKE_ERROR", ""
            if whole.get("outcome") == "ok":
                fields = {f["name"]: f["value"] for f in whole["result"]["fields"]}
                whole_status = fields["status"]["value"]
                whole_diag = fields["diagnostic"]["value"]
            record(f"{name}: fixture stage map", False, "observed", "checker-valid",
                   json.dumps({"tops": tops, "unit": unit,
                               "whole": {"status": whole_status,
                                         "diagnostic": whole_diag[:120]}}))
            return {"stage": "ok", "unit": unit, "tops": tops}

        # ---- CL1 self-referential union ----------------------------------
        r = run_fixture("cl1-self-union", SELF_UNION, 0, None)
        if r.get("stage") == "ok":
            unit = r["unit"]
            expr_ids = [tid for tid, kind, text in r["tops"] if kind == "union_declaration"]
            ok = (unit["status"] == "unsupported" or
                  sorted(unit["ids"]) == sorted(set(expr_ids)))
            record("CL1 self-referential union: terminates; emitted unit's prereqs "
                   "are EXACTLY the union declaration (self deduplicated)", True,
                   "refused-or-exact-self",
                   "refused-or-exact-self" if ok else "mismatch",
                   json.dumps({"unit": unit, "union_ids": expr_ids, "tops": r["tops"]}))
        else:
            record("CL1 self-referential union: terminates; emitted unit's prereqs "
                   "are EXACTLY the union declaration (self deduplicated)", True,
                   "refused-or-exact-self", "unreachable",
                   json.dumps(r.get("diags")))

        # ---- CL2 mutually recursive unions --------------------------------
        r = run_fixture("cl2-mutual-unions", MUTUAL_UNIONS, 0, None)
        cl2_expect = "refused-somewhere-or-exact-both"
        if r.get("stage") == "checker-invalid":
            cl2_obs, cl2_detail = "refused-at-checker", json.dumps(r.get("diags"))
        elif r.get("stage") == "ok":
            unit = r["unit"]
            union_ids = sorted(tid for tid, kind, text in r["tops"]
                               if kind == "union_declaration")
            if unit["status"] == "unsupported":
                cl2_obs, cl2_detail = "refused-at-unit", unit["diagnostic"][:160]
            elif sorted(unit["ids"]) == union_ids:
                cl2_obs, cl2_detail = "exact-both", json.dumps(
                    {"unit": unit, "union_ids": union_ids})
            else:
                cl2_obs, cl2_detail = "wrong-set", json.dumps(
                    {"unit": unit, "union_ids": union_ids})
        else:
            cl2_obs, cl2_detail = r.get("stage"), json.dumps(r)[:200]
        cl2_outcome = cl2_expect if cl2_obs in ("refused-at-checker", "refused-at-unit",
                                                "exact-both") else cl2_obs
        record("CL2 mutually recursive unions: refused at some stage, or the emitted "
               "unit's prereqs are EXACTLY both unions", True, cl2_expect,
               cl2_outcome, f"observed={cl2_obs} {cl2_detail}")

        # ---- CL3 type declared after use, inside closure -------------------
        r = run_fixture("cl3-forward-in-prereq", FORWARD_IN_PREREQ, 0, None)
        if r.get("stage") == "ok":
            unit = r["unit"]
            decl_ids = sorted(tid for tid, kind, text in r["tops"]
                              if kind in ("record_declaration", "union_declaration"))
            if unit["status"] == "unsupported":
                outcome, detail = "refused-with-diagnostic", unit["diagnostic"][:160]
            elif sorted(unit["ids"]) == decl_ids:
                outcome, detail = "complete-set", json.dumps(
                    {"unit": unit, "declared": decl_ids})
            else:
                outcome, detail = "incomplete-set", json.dumps(
                    {"unit": unit, "declared": decl_ids})
            record("CL3 forward-declared prerequisite chain: refuses with a diagnostic "
                   "or reports BOTH declarations (Inner never silently omitted)", True,
                   "refused-or-complete-set",
                   "refused-or-complete-set" if outcome in
                   ("refused-with-diagnostic", "complete-set") else outcome,
                   f"{outcome} {detail}")
        else:
            record("CL3 forward-declared prerequisite chain: refuses with a diagnostic "
                   "or reports BOTH declarations (Inner never silently omitted)", True,
                   "refused-or-complete-set", "checker-unreachable",
                   json.dumps(r.get("diags")))

        # ---- CL4 field references an undeclared name ------------------------
        r = run_fixture("cl4-undeclared-field", UNDECLARED_FIELD, 0, None)
        if r.get("stage") == "checker-invalid":
            record("CL4 undeclared field name is refused at some stage, never "
                   "silently omitted", True, "refused-somewhere",
                   "refused-somewhere", json.dumps(r.get("diags"))[:200])
        elif r.get("stage") == "ok":
            unit = r["unit"]
            ok = unit["status"] == "unsupported"
            record("CL4 undeclared field name is refused at some stage, never "
                   "silently omitted", True, "refused-somewhere",
                   "refused-somewhere" if ok else "emitted-with-unresolved",
                   json.dumps({"unit": unit}))
        else:
            record("CL4 undeclared field name is refused at some stage, never "
                   "silently omitted", True, "refused-somewhere", r.get("stage"),
                   json.dumps(r)[:200])
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
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # harness failure must NOT read as falsification
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
