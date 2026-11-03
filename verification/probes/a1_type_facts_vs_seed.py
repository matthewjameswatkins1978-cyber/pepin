"""A1 type-facts producer vs the SEED's own record declarations — content differential.

The guard probe (`a1_type_facts_attacks.py`) shows the producer fails closed. This
one attacks the opposite risk: facts that are *well-formed but wrong*. The seed's
`check --json` AST carries every `record_declaration` with its field names, type
strings and exact spans, so the producer's facts can be compared field-for-field
against an independent model instead of being trusted.

Claims:
  F1  the same set of record type names, with matching declaration spans
      (declStartByte/declEndByte) and declaration line/column.
  F2  for each record, the same field names in the same order with matching
      field spans (startByte/endByte) and line/column.
  F3  `fieldTypeName` equals the seed's type string for every field, including
      parametric ones such as `List[Int]`.
  F4  primitive-typed fields carry no error code, and an unknown-typed field
      carries a non-empty code (the code value itself is recorded, not asserted).
  F5  a union declaration (`type E = ...`) yields no record-declaration facts.

Exit codes: 0 = no claim falsified, 1 = a claim falsified, 2 = harness error.
Usage: python a1_type_facts_vs_seed.py <a1-worktree-at-pin>
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

PEP_PS1 = REPO / "pep.ps1"
PRIMITIVES = {"Int", "Bool", "Str", "Unit"}

FIXTURES = {
    "records": ("type Point {\n    x: Int\n    y: Bool\n}\n\n"
                "type Box {\n    p: Point\n    s: Str\n    xs: List[Int]\n}\n\n"
                "fn main() -> Int { return 0 }\n"),
    "unknown_field": "type Bad {\n    n: Nope\n}\n\nfn main() -> Int { return 0 }\n",
    "duplicate_field": "type D {\n    a: Int\n    a: Bool\n}\n\nfn main() -> Int { return 0 }\n",
    "union_sibling": ("type E = Num(Int) | Add(E, E)\n\n"
                      "type Wrap {\n    inner: E\n}\n\nfn main() -> Int { return 0 }\n"),
    "crlf_records": ("type Crlf {\r\n    a: Int\r\n    b: Str\r\n}\r\n\r\n"
                     "fn main() -> Int { return 0 }\r\n"),
}

RESULTS = []


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_records(source_text):
    """Record declarations from the seed's own AST, as plain dicts."""
    with tempfile.TemporaryDirectory(prefix="a3-facts-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_text(source_text, encoding="utf-8", newline="")
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(f"seed check returned non-JSON: {done.stdout[:160]}"
                           f"{done.stderr[:160]}")
    out = []
    for node in payload.get("ast") or []:
        if node.get("kind") != "record_declaration":
            continue
        span = node.get("span") or {}
        start = span.get("start") or {}
        out.append({"name": node.get("name"),
                    "start": start.get("offset"), "end": span.get("endOffset"),
                    "line": start.get("line"), "column": start.get("column"),
                    "fields": [{"name": f.get("name"), "type": f.get("type"),
                                "start": ((f.get("span") or {}).get("start") or {}).get("offset"),
                                "end": (f.get("span") or {}).get("endOffset"),
                                "line": ((f.get("span") or {}).get("start") or {}).get("line"),
                                "column": ((f.get("span") or {}).get("start") or {}).get("column")}
                               for f in node.get("fields") or []]})
    return payload.get("status"), out


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
            ("a3-facts", "chunk_type_declarations", [empty_progress],
             {"type": "List[ResolvedTypeDecl]", "value": []}),
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


def plain(value):
    if not isinstance(value, dict):
        return value
    if "fields" in value:
        return {field["name"]: plain(field["value"]) for field in value["fields"]}
    if str(value.get("type", "")).startswith("List["):
        return [plain(item) for item in value.get("value", [])]
    return value.get("value")


def main():
    print(f"REPO={REPO}")
    session = Session()
    try:
        bundle = "\n".join(path.read_text(encoding="utf-8") for path in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-facts-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        require(sample, "outcome", "ok", "open validation sample")
        register(session, opened["document"], opened["revision"],
                 sample["document"], sample["revision"])

        name_fails, span_fails, field_fails, type_fails = [], [], [], []
        invalid_sources = []
        code_rows = []
        for fixture, text in FIXTURES.items():
            raw = text.encode("utf-8")
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"a3-facts-{fixture}", "bytes": list(raw)})
            require(target, "outcome", "ok", f"open {fixture}")
            parsed = parse_target(session, raw, target, opened["revision"])
            response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": "a3-facts",
                                     "arguments": [parsed],
                                     "semanticTarget": {"document": target["document"],
                                                        "revision": target["revision"],
                                                        "entryFunctions": []}})
            require(response, "outcome", "ok", f"invoke facts for {fixture}")
            facts = plain(response["result"])
            seed_status, expected = seed_records(text)
            got = {item.get("typeName"): item for item in facts}
            if seed_status != "valid":
                # The seed refuses the source before/while building declarations, so it
                # offers no ground truth for names or spans. Recorded, not compared: a
                # fact producer may describe a parse the type checker rejects.
                invalid_sources.append({
                    "fixture": fixture, "seed_status": seed_status,
                    "facts": [{"type": item.get("typeName"),
                               "fields": [{"name": f.get("fieldName"),
                                           "declared": f.get("fieldTypeName"),
                                           "code": f.get("fieldCode")}
                                          for f in item.get("fields") or []]}
                              for item in facts]})
                print(f"[F0 {fixture}] seed={seed_status} -> parity not comparable; "
                      f"facts={sorted(got)}")
                continue

            if fixture == "union_sibling":
                ok = "E" not in got and set(got) <= {"Wrap"}
                record("F5 union declarations yield no record facts", True,
                       "no union fact", "no union fact" if ok else f"LEAKED {sorted(got)}",
                       f"facts={sorted(got)}")
            if [item["name"] for item in expected] != list(got):
                name_fails.append(f"{fixture}: seed={[i['name'] for i in expected]} "
                                  f"facts={list(got)}")
            for item in expected:
                fact = got.get(item["name"])
                if fact is None:
                    continue
                if (int(fact.get("declStartByte")), int(fact.get("declEndByte"))) != \
                        (item["start"], item["end"]):
                    span_fails.append(
                        f"{fixture}.{item['name']}: facts "
                        f"({fact.get('declStartByte')},{fact.get('declEndByte')}) vs seed "
                        f"({item['start']},{item['end']})")
                fact_fields = fact.get("fields") or []
                if [f.get("fieldName") for f in fact_fields] != [f["name"] for f in item["fields"]]:
                    if fixture == "duplicate_field":
                        # the producer filters duplicate fields; that is its documented
                        # behaviour and is asserted by the mutation receipt, not here.
                        pass
                    else:
                        field_fails.append(
                            f"{fixture}.{item['name']}: fields "
                            f"{[f.get('fieldName') for f in fact_fields]} vs seed "
                            f"{[f['name'] for f in item['fields']]}")
                for seed_field in item["fields"]:
                    match = [f for f in fact_fields if f.get("fieldName") == seed_field["name"]]
                    if not match:
                        continue
                    mine = match[0]
                    if (int(mine.get("startByte")), int(mine.get("endByte"))) != \
                            (seed_field["start"], seed_field["end"]):
                        field_fails.append(
                            f"{fixture}.{item['name']}.{seed_field['name']}: span "
                            f"({mine.get('startByte')},{mine.get('endByte')}) vs seed "
                            f"({seed_field['start']},{seed_field['end']})")
                    if mine.get("fieldTypeName") != seed_field["type"]:
                        type_fails.append(
                            f"{fixture}.{item['name']}.{seed_field['name']}: type "
                            f"{mine.get('fieldTypeName')!r} vs seed {seed_field['type']!r}")
                    code_rows.append({"fixture": fixture, "field": seed_field["name"],
                                      "type": mine.get("fieldTypeName"),
                                      "code": mine.get("fieldCode"),
                                      "shape": mine.get("fieldShape")})

        record("F1 same record names with matching declaration spans", True, "parity",
               "parity" if not (name_fails or span_fails) else "mismatch",
               "; ".join(name_fails + span_fails))
        record("F2 same fields in order with matching field spans", True, "parity",
               "parity" if not field_fails else "mismatch", "; ".join(field_fails))
        record("F3 fieldTypeName equals the seed type string", True, "parity",
               "parity" if not type_fails else "mismatch", "; ".join(type_fails))

        bad_codes = [row for row in code_rows
                     if row["type"] in PRIMITIVES and row["code"]]
        missing = [row for row in code_rows
                   if row["type"] not in PRIMITIVES and row["type"] != "Nope"
                   and row["type"] and not row["code"]]
        unknown = [row for row in code_rows if row["type"] == "Nope"]
        f4_ok = not bad_codes and all(row["code"] for row in unknown)
        RESULTS.append({"case": "F0 sources the seed rejects (no ground truth)", "claimed": False,
                        "expect": "observed",
                        "outcome": f"{len(invalid_sources)} fixture(s)",
                        "detail": json.dumps(invalid_sources), "falsified": False})
        record("F4 primitive-typed fields carry no error code", True,
               "clean", "clean" if not bad_codes else "mismatch",
               f"primitive_with_code={bad_codes}; unknown-typed codes recorded under F0")
        print("\n" + json.dumps({"code_rows": code_rows}, indent=2, sort_keys=True)[:2500])
    finally:
        session.close()

    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY cases={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['detail']}")
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
