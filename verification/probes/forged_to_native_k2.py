"""Campaign K / A3 K2: does a SAME-TARGET forged callee fact reach a native boundary?

K1 established that at A1 `727f8af` a same-target forged callee fact turns a whole-source
INVALID program into a VALID chunk report. This probe follows that admitted report into the
emitter, through the real tool API the seam probe uses:

  analyse_chunk_typed(full parsed, forged facts)  -> valid report
  emit section "header"  (parsed, report)         -> prelude + prototypes from PARSED NODES
  emit unit idx 0        (parsed, report)         -> scale definition
  emit unit idx 1        (parsed, report)         -> main definition (the forged call site)
  emit section "main"    (parsed, report)         -> epilogue
  assemble -> strict Clang / GCC

Source expectation being tested (not assumed): `pep_c23_call_argument` and the prototype loop
read `parsed.nodes`, so emitted C should be AST-driven and therefore identical whether the
facts were honest or forged. If so the forgery cannot fabricate a binary: the earliest refusal
is the C compiler on a Str-typed argument to an int64_t parameter.

Bundle = A1 lexer/parser/checker @ 727f8af + A2 emitter @ 123d8b3. That composition is exactly
the seam probe's long-standing pin pair; it is a probe over an explicit source set, NOT an
integration claim for either branch.

Usage: python forged_to_native_k2.py <a1-tree-at-727f8af> <a2-emitter.pep>
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

A1 = pathlib.Path(sys.argv[1]).resolve()
EMITTER = pathlib.Path(sys.argv[2]).resolve()
OUT = A1 / "_build" / "a3-k2"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(A1))
import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require, typed  # noqa: E402


def _load(name, candidates):
    for candidate in candidates:
        if candidate.exists():
            spec = importlib.util.spec_from_file_location(name, candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise SystemExit(f"cannot find {name}")


helper = _load("a3_chunk_helper", [A1 / "_build" / "a1_chunk_helper.py",
                                   A1 / "tests" / "chunk_helper.py"])
contract = _load("pep_chunk_contract", [A1 / "pep_chunk_contract.py"])
fields_map, nval, remap_chunk = helper.fields_map, helper.nval, helper.remap_chunk

# Whole-source INVALID: Str argument to an Int parameter.
SRC = ("fn scale(v: Int) -> Int {\n  return v * 2\n}\n"
       "fn main() -> Int {\n  return scale(\"oops\")\n}\n")

CLAIMS = []


def claim(name, ok, detail):
    CLAIMS.append((name, ok))
    print(f"{'HELD    ' if ok else 'FALSIFIED'} {name} :: {detail}")


def main():
    print(f"A1 {A1}")
    print(f"EMITTER {EMITTER}")

    session = Session()
    try:
        bundle = "\n".join([
            (A1 / "examples" / "pep_lexer.pep").read_text(encoding="utf-8"),
            (A1 / "examples" / "pep_parser.pep").read_text(encoding="utf-8"),
            (A1 / "tests" / "pep_checker_a13.pep").read_text(encoding="utf-8"),
            EMITTER.read_text(encoding="utf-8"),
        ])
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "k2-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        tool_revision = opened["revision"]
        tool_doc = opened["document"]
        if opened.get("status") != "valid":
            print(f"BUNDLE-INVALID {opened.get('status')} {opened.get('diagnostics')}")
            return 2

        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "k2-validation", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_checked = pep_c23.checker_report(sample["document"], sample["revision"])
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        refused = pep_c23.typed_record("unsupported", (),
                                       "Pep C23 emission requires a top-level function named main")
        registrations = [
            ("pep-c23-parser-start", "parser_start", [], None),
            ("pep-c23-parser-step", "parser_step",
             [pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                          done=True, lex_done=True, lex_stage="done")],
             pep_c23.parser_chunk_value(
                 sample["document"], sample["revision"],
                 pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                             done=True, lex_done=True,
                                             lex_stage="done"))),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
              empty_types, {"type": "Bool", "value": True}], empty_checked),
            ("pep-c23-section", "emit_c23_section",
             [empty_pp, empty_checked, typed("Str", "header")], refused),
            ("pep-c23-unit", "emit_c23_function_unit",
             [empty_pp, empty_checked, typed("Int", 0)], refused),
        ]
        for tool, function, arguments, expect in registrations:
            if expect is None:  # parser-start needs a live cursor expectation
                expect = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_register", "tool": tool, "document": tool_doc,
                          "revision": tool_revision, "function": function})
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": tool_doc, "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            if validated.get("status") != "Validated":
                print(f"VALIDATE-FAILED {tool}: {json.dumps(validated)[:220]}")
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool, "document": tool_doc,
                          "revision": tool_revision})
        print("TOOLS-ACTIVE")

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "k2-program",
                               "bytes": list(SRC.encode("utf-8"))})
        require(target, "outcome", "ok", "open program")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": []}
        parsed = parse_target(session, SRC.encode("utf-8"), target, tool_revision)
        pfields = fields_map(parsed)
        print(f"PARSE status={pfields['status']['value']} nodes={len(pfields['nodes']['value'])}")

        facts = helper.fetch_all_sigs(session, parsed, tool_revision, sem)
        scale = [s for s in facts if s["name"] == "scale"]
        print(f"HONEST scale facts: {[(s['name'], s['ptypes']) for s in scale]}")
        forged = json.loads(json.dumps(scale))
        for sig in forged:
            sig["ptypes"] = [("Str", ("builtin", "Str", 0), 0)]
        print(f"FORGED scale facts: {[(s['name'], s['ptypes']) for s in forged]}")

        def function_id(name):
            for node in pfields["nodes"]["value"]:
                if (nval(node, "kind") == "function"
                        and str(nval(node, "parentId")) == "-1"
                        and nval(node, "text") == name):
                    return int(nval(node, "id"))
            return None

        index = contract.DocumentIndex.from_parsed(parsed)

        def sliced(node_ids):
            nodes = [n for n in pfields["nodes"]["value"]
                     if int(nval(n, "id")) in set(node_ids)]
            chunk = remap_chunk(json.loads(json.dumps(nodes)))
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                        if key == "nodes" else pfields[key])}
                for key in [f["name"] for f in parsed["fields"]]]}

        chunk_scale = sliced(index.subtree(function_id("scale")))
        chunk_main = sliced(index.subtree(function_id("main")))

        def analyse(progress, sigs):
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [progress,
                               {"type": "List[CheckedFunction]",
                                "value": [helper.checked_fn_value(s) for s in sigs]},
                               {"type": "List[ResolvedSignature]",
                                "value": [helper.resolved_sig_value(s) for s in sigs]},
                               empty_types, {"type": "Bool", "value": True}],
                 "semanticTarget": sem})
            require(response, "outcome", "ok", "analyze_chunk_typed")
            return response["result"]

        report_scale = analyse(chunk_scale, [])
        honest_report = analyse(chunk_main, scale)
        forged_report = analyse(chunk_main, forged)

        def report_status(report):
            fields = fields_map(report)
            return fields["status"]["value"]

        print(f"REPORT scale={report_status(report_scale)} honest={report_status(honest_report)} "
              f"forged={report_status(forged_report)}")
        claim("honest facts keep the caller chunk invalid (control)",
              report_status(honest_report) == "invalid", report_status(honest_report))
        claim("forged facts make the same caller chunk VALID (K1 reproduced at K2)",
              report_status(forged_report) == "valid", report_status(forged_report))
        claim("callee's own chunk is valid without facts (emission prerequisite)",
              report_status(report_scale) == "valid", report_status(report_scale))

        def section(progress, report, part):
            return session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-section",
                 "arguments": [progress, report, typed("Str", part)],
                 "semanticTarget": sem})

        def unit(progress, report, index_in_chunk):
            return session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-unit",
                 "arguments": [progress, report, typed("Int", index_in_chunk)],
                 "semanticTarget": sem})

        def emission_text(response, label):
            if response.get("outcome") != "ok":
                return None, f"TRANSPORT {(response.get('error') or {}).get('code')}"
            fields = fields_map(response["result"])
            status = fields.get("status", {}).get("value")
            if status != "emitted":
                return None, f"{status}: {fields.get('diagnostic', {}).get('value', '')[:90]}"
            parts = fields.get("sourceParts", {}).get("value") or []
            return "".join(p["value"] for p in parts), None

        header, header_err = emission_text(section(chunk_scale, report_scale, "header"), "header")
        scale_unit, scale_err = emission_text(unit(chunk_scale, report_scale, 0), "unit-scale")
        main_unit, main_err = emission_text(unit(chunk_main, forged_report, 0), "unit-main")
        epilogue, epi_err = emission_text(section(chunk_main, forged_report, "main"), "epilogue")
        for label, text, err in (("header", header, header_err),
                                 ("scale-unit", scale_unit, scale_err),
                                 ("main-unit", main_unit, main_err),
                                 ("epilogue", epilogue, epi_err)):
            print(f"EMIT {label:11s} -> {'OK ' + str(len(text)) + 'B' if text else err}")

        claim("emitter still produces C from the forged-valid report",
              all(t is not None for t in (header, scale_unit, main_unit, epilogue)),
              f"header={header is not None} scale={scale_unit is not None} main={main_unit is not None} epi={epilogue is not None}")

        if main_unit:
            passes_str = "pep_str" in main_unit or "(const unsigned char *)" in main_unit
            print(f"MECHANISM main unit passes a Str-typed argument: {passes_str}")
            claim("emitted call site lowers the Str argument by AST, not by the forged fact",
                  passes_str, f"pep_str present={passes_str}")
        if header:
            proto = [line for line in header.split("\n") if "pep_fn_scale" in line]
            print(f"MECHANISM prototype from parsed nodes: {proto[:2]}")

        if all(t is not None for t in (header, scale_unit, main_unit, epilogue)):
            c_path = OUT / "forged.c"
            c_path.write_text(header + scale_unit + main_unit + epilogue,
                              encoding="utf-8", newline="\n")
            print(f"ASSEMBLED {len(c_path.read_text(encoding='utf-8'))}B -> {c_path}")
            for compiler in ("clang", "gcc"):
                exe = OUT / f"forged_{compiler}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler)), "-std=c23", "-Wall", "-Wextra",
                     "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False, cwd=str(A1))
                if built.returncode:
                    first = next((ln for ln in built.stderr.split("\n")
                                  if "error" in ln.lower()), built.stderr.strip()[:140])
                    print(f"C-{compiler.upper()} REFUSED rc={built.returncode}: {first.strip()[:170]}")
                    claim(f"{compiler}: forged-valid chunk cannot be compiled to a binary",
                          True, "compiler refused")
                else:
                    done = subprocess.run([str(exe)], capture_output=True, cwd=str(A1),
                                          check=False)
                    print(f"C-{compiler.upper()} COMPILED rc={done.returncode} "
                          f"out={done.stdout.decode('utf-8', 'replace').strip()[:40]!r}")
                    claim(f"{compiler}: forged-valid chunk cannot be compiled to a binary",
                          False, "compiled and ran — native consequence real")
        else:
            print("C-COMPILE SKIPPED (emission incomplete) — recorded as NOT VERIFIED")

        held = sum(1 for _, ok in CLAIMS if ok)
        print(f"SUMMARY claims={len(CLAIMS)} held={held} falsified={len(CLAIMS) - held}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
