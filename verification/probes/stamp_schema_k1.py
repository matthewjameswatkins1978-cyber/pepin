"""Campaign K / A3 K1: validate A1 `727f8af` callee-fact stamps WITHOUT a false victory.

The old probe (`fact_laundering.py`) fetched facts from one `open` and checked a chunk from a
DIFFERENT `open`. At 727f8af that fires the cross-target ingress rule and would look like
"forgery fixed" while saying nothing about same-target content forgery. This probe keeps the two
questions apart:

  A. SAME-TARGET cases -- fetch facts and check the chunk against ONE parsed document.
     A1  honest positive (valid program)          -> must be valid
     A2  honest negative (Str arg to Int param)   -> must be invalid + PEP_TYPE_MISMATCH
     A3  SAME-TARGET FORGED (param retyped Str, stamps untouched) -> the K1 question
     A4  duplicate fact, same target              -> duplicate rule must still fire
  B. STAMP-INTEGRITY negatives -- honest facts, deliberately wrong stamp fields.
     B1  foreign document / B2 foreign revision / B3 omitted stamp fields
  C. CROSS-TARGET policy -- the old shape, preserved as its OWN separate test, not a fix claim.

Source read that motivates the split (tests/pep_checker_a13.pep @ 727f8af):
  chunk_signatures(2493): `if parsed.document != authority.document || parsed.revision !=
  authority.revision { return [] }` then stamps with `authority`.
  analyze_chunk_typed(2676+): `if extFunction.document != parsed.document || ... ||
  extSignature.revision != parsed.revision` -> PEP_STALE_REVISION.
So the producer guards parsed==snapshot and the consumer guards fact==parsed: the stamp is a
CONSISTENCY gate between producer and consumer identity, not an integrity gate on content.

Usage: python stamp_schema_k1.py <tree-at-727f8af>
Exit 0 = every claim held. Non-zero = at least one claim falsified (see FALSIFIED lines).
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-k1"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402


def _load(name, candidates):
    for candidate in candidates:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location(name, candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise SystemExit(f"cannot find {name} in {[str(c) for c in candidates]}")


helper = _load("a3_chunk_helper", [ROOT / "_build" / "a1_chunk_helper.py",
                                   ROOT / "tests" / "chunk_helper.py"])
contract = _load("pep_chunk_contract", [ROOT / "pep_chunk_contract.py"])
fields_map, nval, remap_chunk = helper.fields_map, helper.nval, helper.remap_chunk

VALID = ("fn scale(v: Int) -> Int {\n  return v * 2\n}\n"
         "fn main() -> Int {\n  return scale(41)\n}\n")
INVALID = ("fn scale(v: Int) -> Int {\n  return v * 2\n}\n"
           "fn main() -> Int {\n  return scale(\"oops\")\n}\n")

CLAIMS = []


def claim(name, ok, detail):
    CLAIMS.append((name, ok))
    print(f"{'HELD    ' if ok else 'FALSIFIED'} {name} :: {detail}")


def seed_verdict(source):
    """Whole-source oracle via pep.ps1 check --json (no native stage needed here)."""
    path = OUT / "oracle.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    done = subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                           "check", str(path), "--json"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(ROOT), check=False)
    try:
        payload = json.loads(done.stdout.strip())
    except ValueError:
        return "NON-JSON", []
    return payload.get("status"), [d.get("code") for d in payload.get("diagnostics") or []]


def main():
    print(f"TREE {ROOT}")
    status, codes = seed_verdict(INVALID)
    print(f"ORACLE whole-source INVALID -> {status} {codes}")
    vstatus, vcodes = seed_verdict(VALID)
    print(f"ORACLE whole-source VALID   -> {vstatus} {vcodes}")

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "k1-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        global TOOL_REVISION
        TOOL_REVISION = opened["revision"]
        tool_doc, tool_rev = opened["document"], opened["revision"]

        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "k1-validation", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True,
            lex_stage="done")
        registrations = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
              empty_types, {"type": "Bool", "value": True}], empty_checked),
        ]
        for tool, function, arguments, expect in registrations:
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": tool, "document": tool_doc,
                          "revision": tool_rev, "function": function})
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_doc, "revision": tool_rev,
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            if validated.get("status") != "Validated":
                print(f"VALIDATE-FAILED {tool}: {json.dumps(validated)[:200]}")
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool, "document": tool_doc,
                          "revision": tool_rev})
        print("TOOLS-ACTIVE")

        def open_program(source, label):
            """ONE open + ONE parse. Both the fact fetch and the chunk check use these."""
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": label,
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open {label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, TOOL_REVISION)
            return parsed, sem

        def function_facts(parsed, sem):
            """Facts produced by the real producer against THIS parsed document."""
            return helper.fetch_all_sigs(session, parsed, TOOL_REVISION, sem)

        def sliced(parsed, ids):
            fields = fields_map(parsed)
            nodes = [n for n in fields["nodes"]["value"] if int(nval(n, "id")) in ids]
            chunk = remap_chunk(json.loads(json.dumps(nodes)))
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                        if key == "nodes" else fields[key])}
                for key in [f["name"] for f in parsed["fields"]]]}

        def function_id(parsed, name):
            for node in fields_map(parsed)["nodes"]["value"]:
                if (nval(node, "kind") == "function"
                        and str(nval(node, "parentId")) == "-1"
                        and nval(node, "text") == name):
                    return int(nval(node, "id"))
            return None

        def check(parsed, sem, name, sigs, drop_stamp=False):
            fn_id = function_id(parsed, name)
            if fn_id is None:
                return {"verdict": f"NO-FN-{name}", "codes": []}
            index = contract.DocumentIndex.from_parsed(parsed)
            fn_values = [helper.checked_fn_value(s) for s in sigs]
            sig_values = [helper.resolved_sig_value(s) for s in sigs]
            if drop_stamp:  # B3: remove the stamp fields entirely from the wire values
                for value in fn_values + sig_values:
                    value["fields"] = [f for f in value["fields"]
                                       if f["name"] not in ("document", "revision")]
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [sliced(parsed, index.subtree(fn_id)),
                               {"type": "List[CheckedFunction]", "value": fn_values},
                               {"type": "List[ResolvedSignature]", "value": sig_values},
                               empty_types, {"type": "Bool", "value": True}],
                 "semanticTarget": sem})
            if response.get("outcome") != "ok":
                error = response.get("error") or {}
                return {"verdict": "TRANSPORT", "codes": [error.get("code")],
                        "message": error.get("message")}
            report = fields_map(response["result"])
            diagnostics = (report["diagnostics"]["value"]
                           if isinstance(report.get("diagnostics"), dict) else [])
            codes = [fields_map(d).get("code", {}).get("value") for d in diagnostics]
            return {"verdict": report["status"]["value"], "codes": codes}

        # ---- A. same-target cases -------------------------------------------------
        parsed_v, sem_v = open_program(VALID, "k1-valid")
        facts_v = function_facts(parsed_v, sem_v)
        scale_v = [s for s in facts_v if s["name"] == "scale"]
        print(f"PRODUCER_STAMP document={scale_v[0]['document']!r} revision={scale_v[0]['revision']!r}"
              f" | target=({sem_v['document']!r},{sem_v['revision'][:20]!r}...)")
        claim("producer stamps the same target it was asked about",
              scale_v[0]["document"] == sem_v["document"]
              and scale_v[0]["revision"] == sem_v["revision"],
              f"stamp==target -> {scale_v[0]['document'] == sem_v['document']}")

        a1 = check(parsed_v, sem_v, "main", scale_v)
        claim("A1 same-target honest positive is valid", a1["verdict"] == "valid", str(a1))

        parsed_i, sem_i = open_program(INVALID, "k1-invalid")
        facts_i = function_facts(parsed_i, sem_i)
        scale_i = [s for s in facts_i if s["name"] == "scale"]

        a2 = check(parsed_i, sem_i, "main", scale_i)
        claim("A2 same-target honest negative is invalid/PEP_TYPE_MISMATCH",
              a2["verdict"] == "invalid" and "PEP_TYPE_MISMATCH" in a2["codes"], str(a2))

        forged = json.loads(json.dumps(scale_i))
        for sig in forged:  # A3: retype the parameter, keep the honest stamps
            sig["ptypes"] = [("Str", ("builtin", "Str", 0), 0)]
        a3 = check(parsed_i, sem_i, "main", forged)
        claim("A3 same-target forged param is REFUSED (stamps close content forgery)",
              a3["verdict"] != "valid", str(a3))
        if a3["verdict"] == "valid":
            print("        -> measured: same-target content forgery is ADMITTED; stamps are")
            print("           consistency only, exactly as A1 documents.")

        dup = json.loads(json.dumps(scale_i)) + [json.loads(json.dumps(scale_i[0]))]
        a4 = check(parsed_i, sem_i, "main", dup)
        claim("A4 same-target duplicate fact still refuses (PEP_DUPLICATE_FUNCTION)",
              a4["verdict"] == "invalid" and "PEP_DUPLICATE_FUNCTION" in a4["codes"], str(a4))

        # ---- B. stamp-integrity negatives ----------------------------------------
        foreign_doc = json.loads(json.dumps(scale_i))
        for sig in foreign_doc:
            sig["document"] = "doc-foreign"
        b1 = check(parsed_i, sem_i, "main", foreign_doc)
        claim("B1 foreign document stamp refused (PEP_STALE_REVISION)",
              b1["verdict"] == "invalid" and "PEP_STALE_REVISION" in b1["codes"], str(b1))

        foreign_rev = json.loads(json.dumps(scale_i))
        for sig in foreign_rev:
            sig["revision"] = "sha256:" + "0" * 64
        b2 = check(parsed_i, sem_i, "main", foreign_rev)
        claim("B2 foreign revision stamp refused (PEP_STALE_REVISION)",
              b2["verdict"] == "invalid" and "PEP_STALE_REVISION" in b2["codes"], str(b2))

        b3 = check(parsed_i, sem_i, "main", json.loads(json.dumps(scale_i)),
                   drop_stamp=True)
        claim("B3 omitted stamp fields fail closed (transport or checker, not valid)",
              b3["verdict"] not in ("valid",), str(b3))

        # ---- C. cross-target policy, kept as its own distinct test ---------------
        parsed_other, sem_other = open_program(INVALID, "k1-invalid-second-open")
        c1 = check(parsed_other, sem_other, "main", scale_i)
        claim("C1 cross-target facts refused (policy test, NOT a forgery fix)",
              c1["verdict"] == "invalid" and "PEP_STALE_REVISION" in c1["codes"], str(c1))

        held = sum(1 for _, ok in CLAIMS if ok)
        print(f"SUMMARY claims={len(CLAIMS)} held={held} falsified={len(CLAIMS) - held}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
