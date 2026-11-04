"""H-V3: can a forged callee fact launder an INVALID whole-source program past the chunk checker?

Property under test (metamorphic, invalid->valid is the forbidden direction):
    whole-source check(invalid)  ==  chunked check(must stay invalid)

Program L is invalid as written (a Str argument to an Int parameter). The only thing that can
make the CALLER chunk valid is the external fact set supplied for the callee -- i.e. a
self-consistent but false statement about the callee's parameter type. This is the exact
authority question the chunk contract has to answer, and it is NOT the same as the E2b/T-ADM-4
duplicate-fact attacks already pinned.

Cases:
  S0  whole-source seed verdict + diagnostic codes            (the oracle)
  A1  chunk main, HONEST facts for scale  -> must stay invalid  (control)
  A2  chunk main, FORGED facts (scale takes Str) -> measured    (the attack)
  A3  chunk main, FORGED return (scale -> Str) with a Str use    (second axis)
  A4  HONEST positive control: valid program, correct facts     (must stay valid)

If A2/A3 come back valid, the payload is the divergence itself: the same bytes are invalid
whole-source and accepted through a chunk. Native consequence is then traced (strict C).

Usage: python fact_laundering.py <a2-tree-with-_build>
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = ROOT / "_build" / "a3-hv3"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

# The cold clone carries no tests/__init__.py and prepare() extracts A1's helper as
# _build/a1_chunk_helper.py; load whichever exists by path (no user-tree modification).
import importlib.util  # noqa: E402


def _load_module(name, candidates):
    for candidate in candidates:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location(name, candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise SystemExit(f"cannot find {name}; looked in {[str(c) for c in candidates]}")


helper = _load_module("a3_chunk_helper", [ROOT / "_build" / "a1_chunk_helper.py",
                                          ROOT / "tests" / "chunk_helper.py"])
checked_fn_value = helper.checked_fn_value
fields_map = helper.fields_map
nval = helper.nval
remap_chunk = helper.remap_chunk
fetch_all_sigs = helper.fetch_all_sigs
resolved_sig_value = helper.resolved_sig_value
contract = _load_module("pep_chunk_contract", [ROOT / "pep_chunk_contract.py"])

SEED = ROOT / "_build" / "a1_seed" / "pep.exe"
# Tool revision is the opened bundle's content revision (sha256:...), not a constant;
# pep_c23.invoke_tool asserts the response echoes it.
TOOL_REVISION = None

# Invalid whole-source: scale takes Int, main passes a Str literal.
INVALID = ('fn scale(v: Int) -> Int {\n  return v * 2\n}\n'
           'fn main() -> Int {\n  return scale("oops")\n}\n')
# Honest positive control: same shape, valid argument.
VALID = ('fn scale(v: Int) -> Int {\n  return v * 2\n}\n'
         'fn main() -> Int {\n  return scale(21)\n}\n')
# Second axis: callee claims a Str result, caller uses it as a Str.
RETURN_AXIS = ('fn label(v: Int) -> Int {\n  return v\n}\n'
               'fn main() -> Int {\n  say(label(7))\n  return 0\n}\n')


def seed_verdict(source):
    path = OUT / "seed_probe.pep"
    path.write_text(source, encoding="utf-8", newline="\n")
    if SEED.exists():
        command = [str(SEED), "run", str(path)]
    else:
        command = ["pwsh", "-NoProfile", "-File", str(ROOT / "pep.ps1"),
                   "check", str(path), "--json"]
    done = subprocess.run(command, capture_output=True, cwd=str(ROOT), check=False)
    payload = None
    try:
        payload = json.loads(done.stdout.decode("utf-8", "replace"))
    except ValueError:
        pass
    if payload:
        return payload.get("status"), [d.get("code") for d in payload.get("diagnostics") or []]
    # `run` prints program output, not JSON: fall back to check-equivalent text.
    text = (done.stdout.decode("utf-8", "replace") + done.stderr.decode("utf-8", "replace"))
    code = next((c for c in ("PEP_TYPE_MISMATCH", "PEP_UNKNOWN_TYPE",
                             "PEP_DUPLICATE_FUNCTION") if c in text), None)
    return ("invalid" if done.returncode else "valid"), [code] if code else []


def main():
    failures = 0
    print(f"INVALID_SHA256 {__import__('hashlib').sha256(INVALID.encode()).hexdigest()}")
    s0_status, s0_codes = seed_verdict(INVALID)
    print(f"S0  whole-source INVALID -> status={s0_status} codes={s0_codes}")
    v0_status, v0_codes = seed_verdict(VALID)
    print(f"S0b whole-source VALID   -> status={v0_status} codes={v0_codes}")

    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "launder-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        global TOOL_REVISION
        TOOL_REVISION = opened["revision"]
        # Registration mirrors tests/probe_seam_chunked.py:183-231 exactly: tools are registered
        # against the BUNDLE document/revision, validated against an empty "sample" program
        # (target_spec), then invoked later with each program's own semanticTarget.
        tool_doc, tool_rev = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "stage-validation", "bytes": []})
        require(sample, "outcome", "ok", "open stage validation source")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(
            sample["document"], sample["revision"], done=True, lex_done=True,
            lex_stage="done")
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        registrations = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
              empty_types, {"type": "Bool", "value": True}], empty_checked),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
        ]
        for tool, function, arguments, expect in registrations:
            registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_register", "tool": tool,
                                      "document": tool_doc, "revision": tool_rev,
                                      "function": function})
            if registered.get("status") not in ("Registered", "Rejected"):
                print(f"REGISTER-UNEXPECTED {tool}: {json.dumps(registered)[:220]}")
                return 2
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_doc, "revision": tool_rev,
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            if validated.get("status") != "Validated":
                print(f"VALIDATE-FAILED {tool}: {json.dumps(validated)[:180]}")
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool, "document": tool_doc,
                          "revision": tool_rev})
        print(f"TOOLS-ACTIVE {[t[0] for t in registrations]}")
        empty_pp = pep_c23.parser_progress(opened["document"], opened["revision"])
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
                 [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
                  empty_types, {"type": "Bool", "value": True}],
                 pep_c23.checker_report(opened["document"], opened["revision"])),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig)):
            pass

        def sliced(parsed, ids):
            fields = fields_map(parsed)
            chunk = parsed_nodes(parsed, ids)
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]",
                                         "value": remap_chunk(json.loads(json.dumps(chunk)))}
                                        if key == "nodes" else fields[key])}
                for key in [field["name"] for field in parsed["fields"]]]}

        def parsed_nodes(parsed, ids):
            return [n for n in fields_map(parsed)["nodes"]["value"] if int(nval(n, "id")) in ids]

        def open_program(source, label):
            target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": label,
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open {label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, TOOL_REVISION)
            return parsed, sem

        def facts_for(source, label):
            parsed, sem = open_program(source, label)
            return fetch_all_sigs(session, parsed, TOOL_REVISION, sem)

        def chunk_verdict(source, label, function, sigs):
            parsed, sem = open_program(source, label)
            index = contract.DocumentIndex.from_parsed(parsed)
            fn_id = None
            for node in fields_map(parsed)["nodes"]["value"]:
                if (nval(node, "kind") == "function"
                        and str(nval(node, "parentId")) == "-1"
                        and nval(node, "text") == function):
                    fn_id = int(nval(node, "id"))
                    break
            if fn_id is None:
                return {"verdict": f"NO-FN-{function}", "codes": []}
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [sliced(parsed, index.subtree(fn_id)),
                               {"type": "List[CheckedFunction]",
                                "value": [checked_fn_value(s) for s in sigs]},
                               {"type": "List[ResolvedSignature]",
                                "value": [resolved_sig_value(s) for s in sigs]},
                               empty_types,
                               {"type": "Bool", "value": True}],
                 "semanticTarget": sem})
            require(response, "outcome", "ok", "analyze_chunk_typed")
            report = fields_map(response["result"])
            diagnostics = (report["diagnostics"]["value"]
                           if isinstance(report.get("diagnostics"), dict) else [])
            codes = []
            for item in diagnostics:
                entry = fields_map(item)
                codes.append(entry.get("code", {}).get("value"))
            return {"verdict": report["status"]["value"], "codes": codes}

        honest = facts_for(VALID, "honest")
        scale_honest = [s for s in honest if s["name"] == "scale"]
        for i, sig in enumerate(scale_honest):
            sig["semid"] = 9000 + i
            sig["synid"] = 1000000000 + i

        forged = json.loads(json.dumps(scale_honest))
        for sig in forged:  # scale claims to take a Str
            sig["ptypes"] = [("Str", ("builtin", "Str", 0), 0)]

        forged_ret = json.loads(json.dumps(scale_honest))
        for sig in forged_ret:  # scale claims to return a Str
            sig["rtype"] = "Str"
            sig["rshape"] = ("builtin", "Str", 0)

        cells = [
            ("A1 honest-facts", INVALID, "a1", "main", scale_honest, "invalid"),
            ("A2 forged-param", INVALID, "a2", "main", forged, "invalid"),
            ("A4 honest-valid", VALID, "a4", "main", scale_honest, "valid"),
        ]
        for name, source, label, function, sigs, expect in cells:
            result = chunk_verdict(source, label, function, sigs)
            ok = result["verdict"] == expect
            status = "HELD" if ok else "FALSIFIED"
            if not ok:
                failures += 1
            print(f"{name:18s} -> {result['verdict']:10s} codes={result['codes']} "
                  f"expect={expect} {status}")

        label_sigs = facts_for(RETURN_AXIS, "ret")
        kept = [s for s in label_sigs if s["name"] == "label"]
        for i, sig in enumerate(kept):
            sig["semid"] = 9100 + i
            sig["synid"] = 1000000100 + i
        forged_label = json.loads(json.dumps(kept))
        for sig in forged_label:
            sig["rtype"] = "Str"
            sig["rshape"] = ("builtin", "Str", 0)
        whole_status, whole_codes = seed_verdict(RETURN_AXIS)
        result = chunk_verdict(RETURN_AXIS, "a3", "main", forged_label)
        print(f"A3 forged-return   -> {result['verdict']:10s} codes={result['codes']} "
              f"(whole-source status={whole_status} codes={whole_codes})")
        print(f"SUMMARY cases={len(cells) + 1} falsified={failures}")
    finally:
        session.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
