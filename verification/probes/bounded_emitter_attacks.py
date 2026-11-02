"""Agent 3 adversarial probes for A2's bounded-emitter slices 2–3
(`codex/a2-bounded-emission@eebd5cd`), covering the three attacks A2 asked
for on #16 plus my unchanged re-run inputs.

Attacks:
  CT0 control — record-parameter unit emits and satisfies the provenance
      invariant (every pep_record_<id> in the unit text appears in
      prerequisiteIds and vice versa) — mirrors A2's own green case as
      non-vacuity for the claims below.
  CT1 NON-PREORDER / inconsistent ids (ask 1) — swap the record root's id
      with the main root's id in the parsed transport before the bounded
      request. Anchor: the emitter contract requires failing closed on
      "malformed parent/child relation, or inconsistent metadata".
      Claim: the bounded unit REFUSES (no silent mis-attribution).
  CT2 TYPE DECLARED AFTER ITS USE (ask 2) — forward-reference source.
      OBSERVATION (claim corrected after measurement, disclosed): both the
      seed and the Pep checker ACCEPT this forward reference, so the original
      "checker refuses first" claim was ill-anchored; the probe records seed
      status + checker outcome + attribution result as the gate datum.
      Attribution was consistent there (prereq id == text tag).
  CT3 UNSUPPORTED PREREQUISITE (ask 3) — `Outer` carries a List field
      (checker-valid, emitter-unsupported; the known list-record gap) and
      references `Inner`. Claim: the bounded unit either refuses or
      satisfies the text<->prerequisite provenance invariant. Observation:
      whether Inner (Outer's own reference) is reported — the pre-announced
      direct-facts-not-closure gap, pinned with exact ids.

Pure checker/session emit layer: no native build, no execution.
Exit: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.

Usage: python bounded_emitter_attacks.py <repo-root-at-pin>
"""
import json
import pathlib
import re
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, typed, typed_record  # noqa: E402

RESULTS = []

FIX_CONTROL = ("type Rec { x: Int }\n"
               "fn take(r: Rec) -> Int { return r.x }\n"
               "fn main() -> Int { return take(Rec { x: 1 }) }\n")
FIX_FORWARD = ("fn take(r: Rec) -> Int { return r.x }\n"
               "type Rec { x: Int }\n"
               "fn main() -> Int { return take(Rec { x: 1 }) }\n")
# Record LITERALS need comma separators (space form parse-fails with
# PEP_PARSE_EXPECTED; measured valid in comma form in the same session).
FIX_UNSUPPORTED_PREREQ = ("type Inner { x: Int }\n"
                          "type Outer { i: Inner xs: List[Int] }\n"
                          "fn use_outer(o: Outer) -> Int { return o.i.x }\n"
                          "fn main() -> Int { return use_outer(Outer { i: Inner { x: 1 }, xs: [] }) }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claim_case": claim, "expect": expect,
                    "outcome": outcome, "detail": detail, "falsified": falsified})


def tags_in(text):
    return sorted({int(m) for m in re.findall(r"pep_record_(\d+)", text)})


def main():
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-bounded-attacks", "metadataOnly": True})
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
            ("pep-c23-unit", "emit_c23_function_unit",
             [empty_parsed, empty_checked, typed("Int", 0)], refused),
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

        def prepare(source, name):
            payload = source.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": name, "bytes": list(payload)})
            require(target, "outcome", "ok", f"open {name}")
            semantic = {"document": target["document"], "revision": target["revision"],
                        "entryFunctions": []}
            parsed = pep_c23.parse_target(session, payload, target, tool_revision)
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker",
                                    "arguments": [parsed], "semanticTarget": semantic})
            return parsed, checked, semantic

        def bounded(parsed, checked, semantic, index):
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "pep-c23-bounded-unit",
                                     "arguments": [parsed, checked, typed("Int", index)],
                                     "semanticTarget": semantic})
            if response.get("outcome") != "ok":
                return {"status": "INVOKE_ERROR",
                        "diagnostic": json.dumps(response.get("error"))[:200],
                        "parts": [], "kinds": [], "ids": []}
            fields = {f["name"]: f["value"] for f in response["result"]["fields"]}
            return {"status": fields["status"]["value"],
                    "diagnostic": fields["diagnostic"]["value"],
                    "parts": [p["value"] for p in fields["sourceParts"]["value"]],
                    "kinds": [i["value"] for i in fields["prerequisiteKinds"]["value"]],
                    "ids": [int(i["value"]) for i in fields["prerequisiteIds"]["value"]]}

        def invariant_holds(unit):
            text_tags = set(tags_in("".join(unit["parts"])))
            prereq = set(unit["ids"])
            return text_tags <= prereq and prereq <= text_tags

        # ---- CT0 control --------------------------------------------------
        parsed, checked, semantic = prepare(FIX_CONTROL, "control")
        if checked.get("outcome") != "ok":
            record("CT0 control: record-param unit emits with provenance invariant", True,
                   "emitted+invariant", "CHECK_FAILED",
                   json.dumps(checked.get("error"))[:200])
        else:
            unit = bounded(parsed, checked["result"], semantic, 0)
            ok = (unit["status"] == "emitted" and invariant_holds(unit)
                  and unit["kinds"] == ["record_declaration"] and len(unit["ids"]) == 1)
            record("CT0 control: record-param unit emits with provenance invariant", True,
                   "emitted+invariant",
                   "emitted+invariant" if ok else "mismatch",
                   json.dumps({"status": unit["status"], "kinds": unit["kinds"],
                               "ids": unit["ids"], "text_tags": tags_in("".join(unit["parts"])),
                               "diagnostic": unit["diagnostic"]}))

        # ---- CT1 non-preorder / inconsistent ids (A2 ask 1) ---------------
        tampered_parsed, tampered_checked, tampered_sem = prepare(FIX_CONTROL, "tamper")
        if tampered_checked.get("outcome") == "ok":
            # Swap the record root's id with main's id (breaks preorder identity).
            rec_root, main_root = None, None
            nodes_field = next(f for f in tampered_parsed["fields"] if f["name"] == "nodes")
            for node in nodes_field["value"]["value"]:
                fields = {f["name"]: f["value"] for f in node["fields"]}
                kind = fields["kind"]["value"]
                text = fields["text"]["value"]
                if kind == "record_declaration" and text == "Rec":
                    rec_root = node
                if kind == "function" and text == "main":
                    main_root = node
            rec_id_field = next(f for f in rec_root["fields"] if f["name"] == "id")
            main_id_field = next(f for f in main_root["fields"] if f["name"] == "id")
            rec_id, main_id = rec_id_field["value"]["value"], main_id_field["value"]["value"]
            rec_id_field["value"]["value"] = main_id
            main_id_field["value"]["value"] = rec_id
            unit = bounded(tampered_parsed, tampered_checked["result"], tampered_sem, 0)
            text = "".join(unit["parts"])
            ok = (unit["status"] == "unsupported" or invariant_holds(unit))
            record("CT1 tampered non-preorder ids: bounded unit refuses (or keeps the "
                   "text<->prerequisite invariant)", True, "refused-or-invariant",
                   "refused-or-invariant" if ok else "falsified",
                   json.dumps({"status": unit["status"], "kinds": unit["kinds"],
                               "ids": unit["ids"], "text_tags": tags_in(text),
                               "swapped_ids": [rec_id, main_id],
                               "diagnostic": unit["diagnostic"][:160]}))

        # ---- CT2 type declared after use (A2 ask 2) -----------------------
        # Anchor corrected after measurement (disclosed): BOTH the seed and the
        # Pep checker accept this forward reference, so the original
        # "checker refuses first" claim was ill-anchored — now an OBSERVATION
        # carrying seed status + checker outcome + attribution result for the gate.
        fwd_parsed, fwd_checked, fwd_sem = prepare(FIX_FORWARD, "forward")
        seed_q = session.send({"schemaVersion": 3, "op": "query",
                               "document": fwd_sem["document"],
                               "revision": fwd_sem["revision"]})
        seed_diags = [(d.get("code"), d.get("message"))
                      for d in (seed_q.get("diagnostics") or [])]
        if fwd_checked.get("outcome") != "ok":
            record("CT2 observation: forward-declared type — seed + checker + "
                   "attribution behaviour", False, "observed",
                   "checker-tool-error",
                   json.dumps({"seed_status": seed_q.get("status"),
                               "seed_diags": seed_diags,
                               "error": fwd_checked.get("error")})[:300])
        else:
            unit = bounded(fwd_parsed, fwd_checked["result"], fwd_sem, 0)
            record("CT2 observation: forward-declared type — seed + checker + "
                   "attribution behaviour", False, "observed",
                   "checker-accepted",
                   json.dumps({"seed_status": seed_q.get("status"),
                               "seed_diags": seed_diags,
                               "unit_status": unit["status"],
                               "kinds": unit["kinds"], "ids": unit["ids"],
                               "text_tags": tags_in("".join(unit["parts"]))}))

        # ---- CT3 unsupported prerequisite (A2 ask 3) ----------------------
        up_parsed, up_checked, up_sem = prepare(FIX_UNSUPPORTED_PREREQ, "unsupported-prereq")
        if up_checked.get("outcome") != "ok":
            record("CT3 unsupported-prereq unit: refuses or keeps the provenance "
                   "invariant", True, "refused-or-invariant", "CHECK_FAILED",
                   json.dumps(up_checked.get("error"))[:220])
        else:
            unit = bounded(up_parsed, up_checked["result"], up_sem, 0)
            text = "".join(unit["parts"])
            held = unit["status"] == "unsupported" or invariant_holds(unit)
            record("CT3 unsupported-prereq unit: refuses or keeps the provenance "
                   "invariant", True, "refused-or-invariant",
                   "refused-or-invariant" if held else "falsified",
                   json.dumps({"status": unit["status"], "kinds": unit["kinds"],
                               "ids": unit["ids"], "text_tags": tags_in(text),
                               "diagnostic": unit["diagnostic"][:160]}))
            # O1: the pre-announced direct-not-closure gap, pinned with ids.
            inner_id = None
            outer_id = None
            nodes_field = next(f for f in up_parsed["fields"] if f["name"] == "nodes")
            for node in nodes_field["value"]["value"]:
                fields = {f["name"]: f["value"] for f in node["fields"]}
                if fields["kind"]["value"] in ("record_declaration",) and \
                        str(fields["parentId"]["value"]) == "-1":
                    if fields["text"]["value"] == "Inner":
                        inner_id = int(fields["id"]["value"])
                    if fields["text"]["value"] == "Outer":
                        outer_id = int(fields["id"]["value"])
            record("O1 closure observation: does the unit's prerequisite set include "
                   "Outer's OWN reference (Inner)?", False, "observed",
                   json.dumps({"prereq_ids": unit["ids"], "outer_id": outer_id,
                               "inner_id": inner_id,
                               "inner_in_prereqs": inner_id in unit["ids"]
                               if (inner_id is not None and unit["ids"]) else None,
                               "status": unit["status"]}), "")
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
