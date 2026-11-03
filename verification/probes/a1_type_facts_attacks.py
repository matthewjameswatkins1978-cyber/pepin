"""Adversarial attack on A1's slice-4a type-facts producer (`chunk_type_declarations`).

Why: `0c5f12b` adds a cross-chunk producer of resolved record-field type facts. It
carries explicit guards (semanticSnapshot document/revision equal to the parsed
one, `done`, `status == "complete"`, `tree_is_valid`). Those guards are exactly the
class of check that failed open before (STALE1), so they are attacked rather than
trusted.

Claims (each is a fail-closed expectation):
  T0  control: a matching ParserProgress/target pair yields at least one resolved
      declaration (non-vacuity — without this the rest proves nothing).
  T1  crossed revision (rev1 parse presented under the rev2 target) yields an
      empty list.
  T2  a parse from a foreign document yields an empty list.
  T3  `done = false` yields an empty list.
  T4  `status != "complete"` yields an empty list.
  T5  a tampered node tree (parent at/after child) yields an empty list.
  T6  a duplicate type name yields exactly one declaration for that name, and its
      span is the FIRST declaration's.
  T7  no primitive name is ever returned as a resolved record declaration.
  T8  every returned declaration carries the target document and revision (no
      foreign labels leaking into facts).

Exit codes: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.
Usage: python a1_type_facts_attacks.py <a1-worktree-at-pin>
"""
import copy
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require, typed  # noqa: E402

PRIMITIVES = {"Int", "Bool", "Str", "Unit", "List", "SourceBytes"}

SOURCE = ("type Point {\n"
          "    x: Int\n"
          "    y: Int\n"
          "}\n"
          "type Box {\n"
          "    p: Point\n"
          "    n: Int\n"
          "}\n"
          "fn main() -> Int { return 0 }\n")

DUPLICATE_SOURCE = ("type Dup {\n"
                    "    a: Int\n"
                    "}\n"
                    "type Dup {\n"
                    "    b: Int\n"
                    "}\n"
                    "fn main() -> Int { return 0 }\n")

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
    start_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision)
    finished_cursor = pep_c23.parser_cursor_value(sample_document, sample_revision,
                                                  done=True, lex_done=True, lex_stage="done")
    empty_progress = pep_c23.parser_progress(sample_document, sample_revision)
    for tool, function, arguments, expect in [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample_document, sample_revision, finished_cursor)),
    ]:
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
    # the new producer itself: an empty parse must yield no declarations
    registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                               "op": "tool_register", "tool": "a3-type-facts",
                               "document": document, "revision": revision,
                               "function": "chunk_type_declarations"})
    require(registered, "status", "Registered", "register a3-type-facts")
    validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": "a3-type-facts",
                              "document": document, "revision": revision,
                              "testVectors": [{"arguments": [empty_progress],
                                               "expect": {"type": "List[ResolvedTypeDecl]",
                                                          "value": []},
                                               "semanticTarget": target_spec}]})
    require(validated, "status", "Validated", "validate a3-type-facts")
    activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_activate", "tool": "a3-type-facts",
                              "document": document, "revision": revision})
    require(activated, "status", "Active", "activate a3-type-facts")


def typed_value(value):
    """Plain-Python view of a typed transport value (records and lists)."""
    if not isinstance(value, dict):
        return value
    if "fields" in value:
        return {field["name"]: typed_value(field["value"]) for field in value["fields"]}
    if value.get("type", "").startswith("List["):
        return [typed_value(item) for item in value.get("value", [])]
    return value.get("value")


def declarations(session, parsed, target_document, target_revision, label):
    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": "a3-type-facts",
                             "arguments": [parsed],
                             "semanticTarget": {"document": target_document,
                                                "revision": target_revision,
                                                "entryFunctions": []}})
    if response.get("outcome") != "ok":
        # The host can refuse a crossed/foreign pair before the producer runs
        # (PEP_STALE_REVISION and friends). That is still fail-closed, so it is
        # reported as `refused`, never as a harness error.
        error = response.get("error") or {}
        return {"state": "refused", "code": error.get("code"), "facts": []}
    result = typed_value(response["result"])
    return {"state": "ok", "code": None,
            "facts": result if isinstance(result, list) else []}


def main():
    print(f"REPO={REPO}")
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-type-facts-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "a3-type-facts-vectors", "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        register(session, opened["document"], opened["revision"],
                 sample["document"], sample["revision"])

        source_bytes = SOURCE.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "a3-type-facts-target", "bytes": list(source_bytes)})
        require(target, "outcome", "ok", "open target")
        document, revision = target["document"], target["revision"]
        parsed = parse_target(session, source_bytes, target, opened["revision"])

        # ---- T0 control ---------------------------------------------------
        control = declarations(session, parsed, document, revision, "control")
        matched = control["facts"]
        names = sorted(item.get("typeName") for item in matched)
        record("T0 control: matching pair yields declarations", True,
               "non-empty", "non-empty" if matched else "EMPTY",
               f"names={names}")

        def fail_closed(label, outcome):
            facts = outcome["facts"]
            return ("empty" if not facts else f"LEAKED {len(facts)} facts",
                    f"state={outcome['state']} code={outcome['code']}")

        # ---- T1 crossed revision ------------------------------------------
        advance = session.send({"schemaVersion": 3, "op": "apply_edit",
                                "document": document, "expected_revision": revision,
                                "start_byte": 0, "end_byte": 0, "replacement": "//x\n"})
        require(advance, "outcome", "ok", "advance revision")
        advanced = advance["revision"]
        crossed = declarations(session, parsed, document, advanced, "crossed revision")
        outcome, detail = fail_closed("crossed", crossed)
        record("T1 crossed revision yields no facts", True, "empty", outcome,
               f"{detail}; revisions parsed={revision[:12]}… target={advanced[:12]}…")

        # ---- T2 foreign document -------------------------------------------
        foreign = declarations(session, parsed, "doc-not-this-one", revision, "foreign doc")
        outcome, detail = fail_closed("foreign", foreign)
        record("T2 foreign document yields no facts", True, "empty", outcome, detail)

        # ---- T3 / T4 done/status guards ------------------------------------
        # A mutation that does not actually reach the tool would silently turn the
        # guard test into a duplicate of T0, so each mutation is asserted first.
        not_done = copy.deepcopy(parsed)
        mutated = False
        for field in not_done["fields"]:
            if field["name"] == "done":
                field["value"] = {"type": "Bool", "value": False}
                mutated = True
        if not mutated:
            raise RuntimeError("T3 mutation did not apply (no `done` field in ParserProgress)")
        outcome, detail = fail_closed("done=false",
                                      declarations(session, not_done, document, revision,
                                                   "done=false"))
        record("T3 done=false yields no facts", True, "empty", outcome, detail)

        bad_status = copy.deepcopy(parsed)
        mutated = False
        for field in bad_status["fields"]:
            if field["name"] == "status":
                field["value"] = {"type": "Str", "value": "partial"}
                mutated = True
        if not mutated:
            raise RuntimeError("T4 mutation did not apply (no `status` field)")
        outcome, detail = fail_closed("status=partial",
                                      declarations(session, bad_status, document, revision,
                                                   "status=partial"))
        record("T4 status=partial yields no facts", True, "empty", outcome, detail)

        # ---- T5 tampered tree ----------------------------------------------
        # Give a non-root top-level node itself as its parent: parent >= id is
        # exactly what `tree_is_valid` is supposed to catch.
        tampered = copy.deepcopy(parsed)
        mutated = False
        for field in tampered["fields"]:
            if field["name"] == "nodes":
                for node in field["value"]["value"]:
                    fields = {f["name"]: f for f in node["fields"]}
                    node_id = fields["id"]["value"]["value"]
                    if fields["parentId"]["value"]["value"] == "0" and node_id != "0":
                        fields["parentId"]["value"]["value"] = node_id
                        mutated = True
                        break
        if not mutated:
            raise RuntimeError("T5 mutation did not apply (no child of node 0 found)")
        outcome, detail = fail_closed("tampered",
                                      declarations(session, tampered, document, revision,
                                                   "tampered"))
        record("T5 tampered tree (self-parent) yields no facts", True, "empty", outcome,
               detail)

        # ---- T6 duplicate type name -----------------------------------------
        dup_bytes = DUPLICATE_SOURCE.encode("utf-8")
        dup_target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": "a3-type-facts-dup",
                                   "bytes": list(dup_bytes)})
        require(dup_target, "outcome", "ok", "open duplicate source")
        dup_parsed = parse_target(session, dup_bytes, dup_target, opened["revision"])
        dup_result = declarations(session, dup_parsed, dup_target["document"],
                                  dup_target["revision"], "duplicate")
        dup_facts = dup_result["facts"]
        dup_names = [item.get("typeName") for item in dup_facts if item.get("typeName") == "Dup"]
        first_start = DUPLICATE_SOURCE.index("type Dup")
        # Transport encodes Int as Str, so compare numerically, not as text.
        spans = [int(item.get("declStartByte")) for item in dup_facts
                 if item.get("typeName") == "Dup"]
        ok = len(dup_names) == 1 and spans == [first_start]
        record("T6 duplicate type name keeps the first declaration", True,
               "exactly one, first span", "exactly one, first span" if ok else "mismatch",
               f"count={len(dup_names)} spans={spans} expected={first_start}")

        # ---- T7 / T8 invariants over every returned declaration -------------
        leaks = [item.get("typeName") for item in matched
                 if item.get("typeName") in PRIMITIVES]
        record("T7 no primitive name returned as a record declaration", True,
               "none", "none" if not leaks else f"LEAKED {leaks}")

        wrong_labels = [item.get("typeName") for item in matched
                        if item.get("document") != document
                        or item.get("revision") != revision]
        record("T8 every fact carries the target document and revision", True,
               "all match", "all match" if not wrong_labels else f"MISLABELLED {wrong_labels}",
               json.dumps([{k: v for k, v in item.items() if k in ("typeName", "document")}
                           for item in matched])[:200] if matched else "")
    finally:
        session.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']}")
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
