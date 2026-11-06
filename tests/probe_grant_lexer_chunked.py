"""Chunked SourceBytes->lexer vertical: the grant wrapper + real lexer scan, native.

The mission's first objective is "an honest host-authorised SourceBytes->real Pep lexer
vertical". A single-unit fixture cannot carry it: main plus even one lexer predicate is
53 nodes, over the checker's ceiling (measured). So this builds the same vertical through
the CHUNKED path -- each function checked in its own chunk with the others as external
signatures -- and assembles one translation unit.

Program under test:

  fn ascii_letter(byte: Int) -> Bool { ... }      verbatim from examples/pep_lexer.pep
  fn ascii_digit(byte: Int) -> Bool { ... }       verbatim
  fn ascii_continue(byte: Int) -> Bool { ... }    verbatim
  fn main(source: SourceBytes) -> Int {           the granted entry
    var n = 0
    var o = 0
    while !(byte_length(source) <= o) {
      if ascii_continue(byte_at(source, o)) { n = n + 1 } else {}
      o = o + 1
    }
    return n
  }

So the native binary reads a real file through the host grant and counts its
identifier-continue bytes using the COMPILER'S OWN lexer functions.

The seed oracle cannot use source_bytes() (plain `run` refuses ungranted bytes with
PEP_RUNTIME_SOURCE_CONTEXT), so it iterates the same byte values as a literal Int list --
same bytes, same predicates, different source for the bytes. That is the authority
boundary, labelled as such.

Requires a checker with chunk tooling (A1 11e1294 or later); SKIPS on a tree without it.

MEASURED OUTCOME at A1 a7d3ee1 (2026-11-06):

  chunk ascii_letter   nodes= 24 status=valid
  chunk ascii_digit    nodes= 12 status=valid
  chunk ascii_continue nodes= 10 status=valid
  chunk main           nodes= 29 status=valid
  units emitted: ascii_letter, ascii_digit
  FIRST REFUSAL: unit ascii_continue -> "Pep C23 calls require a known target"

So the CHUNKED CHECK works for the whole vertical (all four chunks, 10-29 nodes each,
well under the single-unit ceiling that refused the same program at 53 nodes onwards),
but the UNIT EMITTER cannot lower ascii_continue's cross-chunk calls -- even though the
chunk report carries two resolved call facts for them (calleeId 9000/9001, syntaxId
6/8, measured). That is the first refusing layer, and it is reported rather than crashed
past.

Run: python tests/probe_grant_lexer_chunked.py
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

BUILD = ROOT / "_build"
A1_SEED = BUILD / "a1_seed" / "pep.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"

SCAN_MAIN = """fn main(source: SourceBytes) -> Int {
  var n = 0
  var o = 0
  while !(byte_length(source) <= o) {
    if ascii_continue(byte_at(source, o)) { n = n + 1 } else {}
    o = o + 1
  }
  return n
}
"""
FIXTURE = ROOT / "examples" / "pep_lexer.pep"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    chunk_helper_path = ROOT / "tests" / "chunk_helper.py"
    if not chunk_helper_path.is_file():
        print("SKIP: no tests/chunk_helper.py (needs A1 11e1294 or later)")
        return 0
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    pfc = load("pfc", ROOT / "tests" / "probe_function_closure.py")
    helper = load("ch", chunk_helper_path)

    lexer_text = LEXER.read_text(encoding="utf-8")
    declaration_text, functions = pfc.split_source(lexer_text)
    by_name = dict(functions)
    fixture = (by_name["ascii_letter"] + "\n" + by_name["ascii_digit"] + "\n" +
               by_name["ascii_continue"] + "\n" + SCAN_MAIN)

    failures = 0
    session = Session()
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")
        pic.register(session, document, revision, sample["document"], sample["revision"])

        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk", "analyze_chunk_typed",
                 [empty_pp, empty_ext, empty_sig,
                  {"type": "List[ResolvedTypeDecl]", "value": []},
                  {"type": "Bool", "value": True}],
                 pep_c23.checker_report(sample["document"], sample["revision"])),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
                ("pep-c23-section", "emit_c23_section",
                 [empty_pp, pep_c23.checker_report(sample["document"], sample["revision"]),
                  typed("Str", "header")],
                 pep_c23.typed_record("unsupported", (),
                                      "Pep C23 emission requires a top-level function "
                                      "named main"))):
            # pic.register already registered pep-c23-unit / pep-c23-declaration-unit,
            # but NOT pep-c23-section.
            _SIGS_SECTION = True
            for op, extra, want in (
                    ("tool_register", {"function": function}, "Registered"),
                    ("tool_validate",
                     {"testVectors": [{"arguments": arguments, "expect": expect,
                                       "semanticTarget": target_spec}]}, "Validated"),
                    ("tool_activate", {}, "Active")):
                resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": op, "tool": tool, "document": document,
                                     "revision": revision, **extra})
                require(resp, "status", want, f"{op} {tool}")

        payload = fixture.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "grant-lexer-chunked", "bytes": list(payload)})
        require(target, "outcome", "ok", "open chunked vertical")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        print(f"sigs: {[s['name'] for s in sigs]}")

        # ---- chunk: each function, callees as externals -----------------------
        labels = ["ascii_letter", "ascii_digit", "ascii_continue", "main"]
        reports, sliced = {}, {}
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            subtree = index.subtree(int(helper.nval(node, "id")))
            chunk_nodes = index.nodes_for(sorted(subtree))
            extra = helper.decl_closure(nodes, chunk_nodes, {}, {}, lambda n: None) \
                if False else []
            keep = set(subtree) | {int(helper.nval(n, "id")) for n in extra}
            chunk_nodes = index.nodes_for(sorted(keep))
            other = [s for s in sigs if s["name"] != label]
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                      if k == "nodes" else pfields[k])} for k in pfields]}
            checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                    "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                    "arguments": [sl,
                                                  {"type": "List[CheckedFunction]",
                                                   "value": [helper.checked_fn_value(s) for s in other]},
                                                  {"type": "List[ResolvedSignature]",
                                                   "value": [helper.resolved_sig_value(s) for s in other]},
                                                  {"type": "List[ResolvedTypeDecl]", "value": []},
                                                  {"type": "Bool", "value": True}],
                                    "semanticTarget": sem})
            if checked.get("outcome") != "ok":
                print(f"chunk {label}: ERROR {(checked.get('error') or {}).get('code')}")
                failures += 1
                continue
            f = fm(checked["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            print(f"chunk {label:15s} nodes={len(chunk_nodes):3d} status={f['status']['value']} {codes[:2]}")
            if f["status"]["value"] != "valid":
                failures += 1
                continue
            reports[label] = checked["result"]
            sliced[label] = sl

        def invoke(tool, arguments, what):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool,
                                 "arguments": arguments, "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                raise RuntimeError(
                    f"{what}: {(resp.get('error') or {}).get('code')}")
            efields = fm(resp["result"])
            if efields["status"]["value"] != "emitted":
                raise RuntimeError(f"{what}: status={efields['status']['value']} "
                                   f"{efields['diagnostic']['value'][:160]}")
            return "".join(p["value"] for p in efields["sourceParts"]["value"])

        def try_invoke(tool, arguments, what):
            """Emit or record the FIRST refusing layer instead of crashing."""
            try:
                return invoke(tool, arguments, what), None
            except RuntimeError as error:
                return None, str(error)

        # ---- emit each chunk, assemble one translation unit -------------------
        header, why = try_invoke("pep-c23-section",
                                 [sliced["ascii_letter"], reports["ascii_letter"],
                                  typed("Str", "header")], "header")
        if header is None:
            print(f"FIRST REFUSAL header: {why}")
            failures += 1
            return 1

        units = ""
        emitted_labels = []
        for label in labels:
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced[label], reports[label], typed("Int", 0)],
                                    f"unit {label}")
            if piece is None:
                print(f"FIRST REFUSAL unit {label}: {why}")
                failures += 1
                break
            units += piece
            emitted_labels.append(label)
        if failures:
            print(f"\nemitted units before the refusal: {emitted_labels}")
            return 1

        prototypes = "".join(
            invoke("pep-c23-section",
                   [sliced[label], reports[label], typed("Str", "prototypes")],
                   f"prototypes {label}") for label in labels)
        epilogue = invoke("pep-c23-section",
                          [sliced["main"], reports["main"], typed("Str", "main")],
                          "epilogue")
        print(f"header={len(header)} prototypes={len(prototypes)} "
              f"units={len(units)} epilogue={len(epilogue)}")
        if "pep_source_data" not in epilogue:
            print("FAIL: epilogue carries no grant wrapper (pep_source_data absent)")
            failures += 1
            return 1

        # Document order (callees before callers) and the prototype-first order that
        # makes unit order irrelevant. Both must compile.
        assembled = {
            "docorder": header + units + epilogue,
            "protofirst": header + prototypes + units + epilogue,
        }
    finally:
        session.close()

    if failures:
        print(f"\nchunked vertical: INCOMPLETE ({failures})")
        return 1

    # ---- real file, seed oracle, both strict compilers -----------------------
    fixture_path = BUILD / "grant_lexer_chunked_input.pep"
    fixture_path.write_text("fn main() -> Int { return 42 }\n", encoding="utf-8",
                            newline="\n")
    payload_bytes = fixture_path.read_bytes()

    oracle = "".join(by_name[n] + "\n"
                     for n in ("ascii_letter", "ascii_digit", "ascii_continue"))
    oracle += "let bytes = [" + ", ".join(str(b) for b in payload_bytes) + "]\n"
    oracle += ("var n = 0\nfor b in bytes { if ascii_continue(b) { n = n + 1 } else {} }\n"
               "say(int_text(n))\n")
    oracle_path = BUILD / "grant_lexer_chunked_oracle.pep"
    oracle_path.write_text(oracle, encoding="utf-8", newline="\n")
    seed = subprocess.run([str(A1_SEED), "run", str(oracle_path)],
                          capture_output=True, check=False)
    if seed.returncode:
        print("seed-oracle FAIL", seed.stderr.decode("utf-8", "replace")[:200])
        return 1
    expected = seed.stdout.replace(b"\r\n", b"\n").strip() + b"\n"
    print(f"seed-oracle OK expected={expected!r}")

    for order, c_source in assembled.items():
        c_path = BUILD / f"grant_lexer_chunked_{order}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"grant_lexer_chunked_{order}_{compiler_name}.exe"
            built = subprocess.run(
                [str(pep_c23.compiler_path(compiler_name)), *extra,
                 "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                 str(c_path), "-o", str(exe)],
                capture_output=True, text=True, check=False)
            if built.returncode:
                print(f"{order}-{compiler_name}: BUILD FAIL {built.stderr[:300]}")
                failures += 1
                continue
            ran = subprocess.run([str(exe), str(fixture_path)],
                                 capture_output=True, check=False)
            out = ran.stdout.replace(b"\r\n", b"\n")
            ok = ran.returncode == 0 and out == expected
            print(f"{order}-{compiler_name}: {'OK' if ok else 'FAIL'} "
                  f"seed={expected!r} native={out!r}")
            if not ok:
                failures += 1

    print("\nchunked SourceBytes->lexer vertical:",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
