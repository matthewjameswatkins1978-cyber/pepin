"""A1 staged check + native assembly of A4's actual dogfood app (LUCY-20261107-007 slice 1).

Derived from A2's tests/probe_grant_lexer_chunked.py (same session harness:
Session open of the compiler bundle, per-function chunk checks with externals,
unit emission, fact negatives, seed oracle, strict Clang+GCC). A1-owned file on
an A1 scratch branch; A2's probe is untouched.

Program under test: examples/dogfood/pepin-source-scan.pep at A4 12e143f,
UNALTERED (sha256 f6e8f942...). Four functions chunked: ascii_letter,
ascii_digit, ascii_continue, main(source: SourceBytes) -> Int.

Run: python tests/probe_dogfood_scan_a1.py
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
APP = ROOT / "examples" / "dogfood" / "pepin-source-scan.pep"
FIXTURES = {
    "ascii": (ROOT / "examples" / "dogfood" / "input_ascii.pep", 23),
    "nonascii": (ROOT / "examples" / "dogfood" / "input_nonascii.pep", 30),
    "empty": (ROOT / "examples" / "dogfood" / "input_empty.pep", 0),
    "self": (APP, 139),
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    chunk_helper_path = ROOT / "tests" / "chunk_helper.py"
    if not chunk_helper_path.is_file():
        print("SKIP: no tests/chunk_helper.py")
        return 0
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    pfc = load("pfc", ROOT / "tests" / "probe_function_closure.py")
    helper = load("ch", chunk_helper_path)

    app_text = APP.read_text(encoding="utf-8")
    declaration_text, functions = pfc.split_source(app_text)
    by_name = dict(functions)
    labels = ["ascii_letter", "ascii_digit", "ascii_continue", "main"]
    missing = [n for n in labels if n not in by_name]
    if missing:
        print(f"FAIL: app functions missing: {missing}")
        return 1
    fixture = "\n".join(by_name[n] for n in labels) + "\n"

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
                               "name": "dogfood-scan-a1", "bytes": list(payload)})
        require(target, "outcome", "ok", "open dogfood app")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        print(f"sigs: {[s['name'] for s in sigs]}")

        # ---- chunk: each function, others as externals -------------------------
        reports, sliced = {}, {}
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            subtree = index.subtree(int(helper.nval(node, "id")))
            chunk_nodes = index.nodes_for(sorted(subtree))
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
        if failures:
            print(f"\nFIRST REFUSAL is in staged checking ({failures} chunk(s) not valid)")
            return 1

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
            return 1

        units = ""
        emitted_labels = []
        for label in labels:
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced[label], reports[label], typed("Int", 0)],
                                    f"unit {label}")
            if piece is None:
                print(f"FIRST REFUSAL unit {label}: {why}")
                print(f"emitted units before the refusal: {emitted_labels}")
                return 1
            units += piece
            emitted_labels.append(label)

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
            return 1

        assembled = {
            "docorder": header + units + epilogue,
            "protofirst": header + prototypes + units + epilogue,
        }

        # ---- negative controls on the real app's call facts --------------------
        def recmap(rec):
            return {f["name"]: f["value"] for f in rec["fields"]}

        def with_field(rec, name, value):
            return {"type": rec["type"], "fields": [
                ({"name": f["name"], "value": value} if f["name"] == name else f)
                for f in rec["fields"]]}

        def expect_refusal(label, report, needle):
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced["main"], report, typed("Int", 0)],
                                    f"negative {label}")
            if piece is not None:
                print(f"NEGATIVE {label}: FAIL (expected refusal, got emission)")
                return 1
            if needle not in why:
                print(f"NEGATIVE {label}: FAIL (refusal {why!r} lacks {needle!r})")
                return 1
            print(f"NEGATIVE {label}: OK ({needle[:64]})")
            return 0

        main_report = reports["main"]
        main_fields = recmap(main_report)
        calls = json.loads(json.dumps(main_fields["calls"]["value"]))
        functions = json.loads(json.dumps(main_fields["functions"]["value"]))
        # Prefer the ascii_continue fact (nested call site); fall back to any fact.
        anchor = next((f for f in calls
                       if recmap(next(x for x in functions
                                      if int(recmap(x)["semanticId"]["value"])
                                      == int(recmap(f)["calleeId"]["value"])) )
                       ["name"]["value"] == "ascii_continue"), None)
        if anchor is None:
            anchor = calls[0] if calls else None
        if anchor is None:
            print("NEGATIVE setup: main carries no resolved call facts at all")
            return 1
        anchor_name = recmap(next(x for x in functions
                                  if int(recmap(x)["semanticId"]["value"])
                                  == int(recmap(anchor)["calleeId"]["value"])) )["name"]["value"]
        print(f"negative anchor: call to {anchor_name}")
        failures += expect_refusal(
            "no-fact", with_field(main_report, "calls",
                                  {"type": "List[ResolvedCall]", "value": []}),
            "Pep C23 cross-chunk call has no resolved call fact")
        severed = with_field(anchor, "calleeId", typed("Int", 999999))
        severed_calls = {"type": "List[ResolvedCall]", "value": [
            severed if recmap(f)["syntaxId"] == recmap(anchor)["syntaxId"] else f
            for f in calls]}
        failures += expect_refusal(
            "missing-target", with_field(main_report, "calls", severed_calls),
            "Pep C23 cross-chunk call target is missing from the checked functions")
        forged_fns = [with_field(f, "arity", typed("Int", 99))
                      if recmap(f)["name"]["value"] == anchor_name else f
                      for f in functions]
        failures += expect_refusal(
            "arity", with_field(main_report, "functions",
                                {"type": "List[CheckedFunction]", "value": forged_fns}),
            "Pep C23 cross-chunk call argument count disagrees with the checked arity")
    finally:
        session.close()

    if failures:
        print(f"\ndogfood scan: INCOMPLETE ({failures})")
        return 1

    # ---- seed oracle: identifier-start runs over literal bytes -----------------
    oracles = []
    for key, (path, expected) in FIXTURES.items():
        raw = path.read_bytes()
        oracle = "".join(by_name[n] + "\n" for n in ("ascii_letter", "ascii_continue"))
        oracle += "let bytes: List[Int] = [" + ", ".join(str(b) for b in raw) + "]\n"
        oracle += ("var n = 0\nvar prev_cont = false\nvar first = true\n"
                   "for b in bytes {\n"
                   "  if ascii_letter(b) { if first { n = n + 1 } else { "
                   "if prev_cont { } else { n = n + 1 } } } else { }\n"
                   "  if ascii_continue(b) { prev_cont = true } "
                   "else { prev_cont = false }\n"
                   "  first = false\n}\n"
                   "say(int_text(n))\n")
        oracle_path = BUILD / f"dogfood_scan_a1_{key}_oracle.pep"
        oracle_path.write_text(oracle, encoding="utf-8", newline="\n")
        seed = subprocess.run([str(A1_SEED), "run", str(oracle_path)],
                              capture_output=True, check=False)
        if seed.returncode:
            print(f"seed-oracle {key}: FAIL "
                  f"{seed.stderr.decode('utf-8', 'replace')[:200]}")
            return 1
        got = seed.stdout.replace(b"\r\n", b"\n").strip()
        ok = got == str(expected).encode()
        print(f"seed-oracle {key}: {'OK' if ok else 'FAIL'} "
              f"expected={expected} seed={got!r} bytes={len(raw)}")
        if not ok:
            return 1
        oracles.append((key, path, expected))

    # ---- native: strict Clang + GCC over every fixture -------------------------
    for order, c_source in assembled.items():
        c_path = BUILD / f"dogfood_scan_a1_{order}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"dogfood_scan_a1_{order}_{compiler_name}.exe"
            built = subprocess.run(
                [str(pep_c23.compiler_path(compiler_name)), *extra,
                 "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                 str(c_path), "-o", str(exe)],
                capture_output=True, text=True, check=False)
            if built.returncode:
                print(f"{order}-{compiler_name}: BUILD FAIL {built.stderr[:300]}")
                failures += 1
                continue
            for key, path, expected in oracles:
                ran = subprocess.run([str(exe), str(path)],
                                     capture_output=True, check=False)
                out = ran.stdout.replace(b"\r\n", b"\n").strip()
                ok = ran.returncode == 0 and out == str(expected).encode()
                print(f"{order}-{compiler_name}/{key}: {'OK' if ok else 'FAIL'} "
                      f"expected={expected} native={out!r}")
                if not ok:
                    failures += 1

    print("\ndogfood source-scan (A1 staged + A2 native):",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
