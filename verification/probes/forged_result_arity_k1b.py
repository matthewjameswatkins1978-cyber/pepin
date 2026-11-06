"""Agent 3 K1b: same-target forged RESULT TYPE and ARITY through the staged chunk checker.

K1 (stamp_schema_k1) established: same-target forged PARAMETER type is ADMITTED
(valid), while duplicates/aliases/foreign/omitted stamps are refused. That left two
same-target content-forgery variants untested: forging the callee's RESULT type and
forging its ARITY. This probe closes exactly those two (+ a strengthened arity lie),
against the candidate tree passed as argv[1], reusing K1's registration flow verbatim.

Hand-supplied facts, NOT executable normal-host attacks: there is no seed oracle for a
forged fact (no such program exists). A `valid` verdict here means ADMISSION of a
same-target content forgery (new residual, same class as K1-A3); any refusal names its
code. Either outcome is recorded, never relabeled.

Exit codes: 0 = probe ran to a verdict (claims printed), 1 = a harness/claim error,
2 = harness error (tool validation failed).
Usage: python forged_result_arity_k1b.py <candidate-worktree>
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-k1b"
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


def seed_verdict(source):
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
    print(f"ORACLE INVALID -> {seed_verdict(INVALID)}")
    print(f"ORACLE VALID   -> {seed_verdict(VALID)}")

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "k1b-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        TOOL_REVISION = opened["revision"]
        tool_doc, tool_rev = opened["document"], opened["revision"]

        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "k1b-validation", "bytes": []})
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
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": label,
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open {label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, TOOL_REVISION)
            return parsed, sem

        def function_facts(parsed, sem):
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

        def check(parsed, sem, name, sigs):
            fn_id = function_id(parsed, name)
            if fn_id is None:
                return {"verdict": f"NO-FN-{name}", "codes": []}
            index = contract.DocumentIndex.from_parsed(parsed)
            fn_values = [helper.checked_fn_value(s) for s in sigs]
            sig_values = [helper.resolved_sig_value(s) for s in sigs]
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

        parsed_v, sem_v = open_program(VALID, "k1b-valid")
        facts_v = function_facts(parsed_v, sem_v)
        scale_v = [s for s in facts_v if s["name"] == "scale"]
        c0 = check(parsed_v, sem_v, "main", scale_v)
        print(f"C0 honest positive (control) -> {c0}")

        parsed_i, sem_i = open_program(INVALID, "k1b-invalid")
        facts_i = function_facts(parsed_i, sem_i)
        scale_i = [s for s in facts_i if s["name"] == "scale"]
        c1 = check(parsed_i, sem_i, "main", scale_i)
        print(f"C1 honest negative (control) -> {c1}")

        # A6: same-target forged RESULT (Int -> Str), honest stamps untouched.
        forged_r = json.loads(json.dumps(scale_i))
        for sig in forged_r:
            sig["rtype"] = "Str"
            sig["rshape"] = ("scalar", "Str", 0)
        a6 = check(parsed_i, sem_i, "main", forged_r)
        print(f"A6 same-target forged RESULT Int->Str -> {a6}")

        # A7: same-target forged ARITY (1 -> 2, ptypes untouched), stamps untouched.
        forged_a = json.loads(json.dumps(scale_i))
        for sig in forged_a:
            sig["arity"] = 2
        a7 = check(parsed_i, sem_i, "main", forged_a)
        print(f"A7 same-target forged ARITY 1->2 -> {a7}")

        # A8: strengthened arity lie (arity 2 + matching second Int param), stamps untouched.
        forged_a2 = json.loads(json.dumps(scale_i))
        for sig in forged_a2:
            sig["arity"] = 2
            sig["ptypes"] = [("Int", ("scalar", "", 0), 0),
                             ("Int", ("scalar", "", 0), 0)]
        a8 = check(parsed_i, sem_i, "main", forged_a2)
        print(f"A8 same-target forged ARITY 2 + matching ptypes -> {a8}")

        admitted = [k for k, r in (("A6", a6), ("A7", a7), ("A8", a8))
                    if r["verdict"] == "valid"]
        print(f"SUMMARY forged-admitted={admitted if admitted else 'none'}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
