"""A1 tracked probe: A4's List shape natively, end-to-end (LUCY-20261107-012).

Fixture: tests/fixtures/list_probe_native.pep (literal list construction in
main + hoisted cross-chunk Int call; for-in sum; build declared but unused by
main). Three gates it deliberately dodges, all measured on #16 6707653621 /
6707686168 / 6707793442:
  - top-level assignment statements (body-shape gate) -> literal/var-init form;
  - nested-arg cross-chunk call `total(build())`       -> two-step hoist;
  - cross-chunk call with List result (type gate, tests/pep_c23_emitter.pep
    "cross-chunk calls support Int, Bool, and locally declared record results")
    -> construct in main; build() emitted but unused.

Pipeline: chunk-check each function (externals = other signatures) -> emit
header/units/prototypes/epilogue through the unit path -> strict Clang C23 +
GCC C2x, docorder AND protofirst -> run each binary, expect 6.

Usage: python tests/probe_list_native.py
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23
from pep_c23 import Session, require, parse_target, typed

BUILD = ROOT / "_build"
FIXTURE = ROOT / "tests" / "fixtures" / "list_probe_native.pep"
EXPECTED = b"6"
LABELS = ["build", "total", "main"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")

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
        pic.register(session, document, revision,
                     sample["document"], sample["revision"])
        target_spec = {"document": sample["document"],
                       "revision": sample["revision"], "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_td = {"type": "List[ResolvedTypeDecl]", "value": []}
        empty_b = {"type": "Bool", "value": True}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk", "analyze_chunk_typed",
                 [empty_pp, empty_ext, empty_sig, empty_td, empty_b],
                 pep_c23.checker_report(sample["document"], sample["revision"])),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
                ("pep-c23-section", "emit_c23_section",
                 [empty_pp, pep_c23.checker_report(sample["document"],
                                                    sample["revision"]),
                  typed("Str", "header")],
                 pep_c23.typed_record("unsupported", (),
                                      "Pep C23 emission requires a top-level "
                                      "function named main"))):
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

        payload = FIXTURE.read_bytes()
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "list-native", "bytes": list(payload)})
        require(target, "outcome", "ok", "open fixture")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        print(f"fixture sha256="
              f"{__import__('hashlib').sha256(payload).hexdigest()[:16]}")
        print(f"sigs: {[s['name'] for s in sigs]}")

        reports, sliced = {}, {}
        for label in LABELS:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            ids = sorted(index.subtree(int(helper.nval(node, "id"))))
            other = [s for s in sigs if s["name"] != label]
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(
                                           json.loads(json.dumps(
                                               index.nodes_for(ids))))}
                                      if k == "nodes" else pfields[k])}
                for k in pfields]}
            checked = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2,
                 "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                 "arguments": [sl,
                               {"type": "List[CheckedFunction]",
                                "value": [helper.checked_fn_value(s) for s in other]},
                               {"type": "List[ResolvedSignature]",
                                "value": [helper.resolved_sig_value(s) for s in other]},
                               empty_td, empty_b],
                 "semanticTarget": sem})
            if checked.get("outcome") != "ok":
                print(f"chunk {label}: TOOL "
                      f"{(checked.get('error') or {}).get('code')}")
                failures += 1
                continue
            f = fm(checked["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            print(f"chunk {label:8s} status={f['status']['value']} {codes[:2]}")
            if f["status"]["value"] != "valid":
                failures += 1
                continue
            reports[label] = checked["result"]
            sliced[label] = sl
        if failures:
            print(f"\nFIRST LAYER: checking ({failures} failed)")
            return 1

        def invoke(tool, arguments, what):
            try:
                resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": tool,
                                     "arguments": arguments, "semanticTarget": sem})
            except RuntimeError as error:
                return None, f"TRANSPORT {error}"
            met = session.send({"schemaVersion": 3, "op": "metrics"})
            steps = (met.get("metrics") or {}).get("last_execute_steps")
            if resp.get("outcome") != "ok":
                return None, (f"{(resp.get('error') or {}).get('code')} "
                              f"steps={steps}")
            ef = fm(resp["result"])
            if ef["status"]["value"] != "emitted":
                return None, (f"status={ef['status']['value']} "
                              f"{ef['diagnostic']['value'][:180]} steps={steps}")
            print(f"  emit {what}: OK steps={steps}")
            return "".join(p["value"] for p in ef["sourceParts"]["value"]), None

        header, why = invoke("pep-c23-section",
                             [sliced["build"], reports["build"],
                              typed("Str", "header")], "header")
        if header is None:
            print(f"FIRST REFUSAL header: {why}")
            return 1
        units = ""
        for label in LABELS:
            piece, why = invoke("pep-c23-unit",
                                [sliced[label], reports[label], typed("Int", 0)],
                                f"unit {label}")
            if piece is None:
                print(f"FIRST REFUSAL unit {label}: {why}")
                return 1
            units += piece
        prototypes = ""
        for label in LABELS:
            piece, why = invoke("pep-c23-section",
                                [sliced[label], reports[label],
                                 typed("Str", "prototypes")],
                                f"prototypes {label}")
            if piece is None:
                print(f"FIRST REFUSAL prototypes {label}: {why}")
                return 1
            prototypes += piece
        epilogue, why = invoke("pep-c23-section",
                               [sliced["main"], reports["main"],
                                typed("Str", "main")], "epilogue")
        if epilogue is None:
            print(f"FIRST REFUSAL epilogue: {why}")
            return 1
        print(f"header={len(header)} prototypes={len(prototypes)} "
              f"units={len(units)} epilogue={len(epilogue)}")

        for order, c_source in (("docorder", header + units + epilogue),
                                ("protofirst",
                                 header + prototypes + units + epilogue)):
            c_path = BUILD / f"list_native_{order}.c"
            c_path.write_text(c_source, encoding="utf-8", newline="\n")
            for compiler_name, extra in (("clang", ["-std=c23"]),
                                         ("gcc", ["-std=c2x"])):
                exe = BUILD / f"list_native_{order}_{compiler_name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler_name)), *extra,
                     "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"{order}-{compiler_name}: BUILD FAIL "
                          f"{built.stderr[:300]}")
                    failures += 1
                    continue
                ran = subprocess.run([str(exe)], capture_output=True, check=False)
                out = ran.stdout.replace(b"\r\n", b"\n").strip()
                ok = ran.returncode == 0 and out == EXPECTED
                print(f"{order}-{compiler_name}: {'OK' if ok else 'FAIL'} "
                      f"expected={EXPECTED!r} native={out!r} rc={ran.returncode}")
                if not ok:
                    failures += 1
    finally:
        session.close()

    print("\nlist-native vertical:",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


sys.exit(main())
