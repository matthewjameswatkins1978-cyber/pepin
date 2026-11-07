"""A3 BOOT-A3-043: does a user-function wrapper make a builtin call emittable?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-043-WRAPPER.md @ d0fa94d,
committed before this probe existed or ran.

Generalises BOOT-A3-042 to N functions: chunk every function with the others as external facts, check
all, report per-function status BEFORE emitting anything, then emit units + grant epilogue, and if all
chunks emit, run the full divergence chain (two unseen inputs -> C differs -> both compile under strict
Clang and GCC -> run to different outputs).

CAPABILITY PROBE, NOT A COMPILER.

Run: python verification/probes/wrapper_variant_043.py [--json]
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

BUILD = ROOT / "_build"
FX = PROBE_ROOT / "verification" / "fixtures" / "divergence"

PROGRAM = (
    'fn slice3(source: SourceBytes) -> Str {\n'
    '  return utf8_slice(source, 0, 3)\n'
    '}\n'
    '\n'
    'fn main(source: SourceBytes) -> Int {\n'
    '  let part = slice3(source)\n'
    '  say("#include <stdio.h>")\n'
    '  say("int main(void){puts(")\n'
    '  say("\\"")\n'
    '  say(part)\n'
    '  say("\\");return 0;}")\n'
    '  return 0\n'
    '}\n'
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    BUILD.mkdir(parents=True, exist_ok=True)
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    session = Session()
    c_source = None
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate",
                               "bytes": []})
        pic.register(session, document, revision, sample["document"], sample["revision"])
        spec = {"document": sample["document"], "revision": sample["revision"],
                "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk", "analyze_chunk_typed",
                 [empty_pp, {"type": "List[CheckedFunction]", "value": []}, empty_sig,
                  {"type": "List[ResolvedTypeDecl]", "value": []}, {"type": "Bool", "value": True}],
                 pep_c23.checker_report(sample["document"], sample["revision"])),
                ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig),
                ("pep-c23-section", "emit_c23_section",
                 [empty_pp, pep_c23.checker_report(sample["document"], sample["revision"]),
                  typed("Str", "header")],
                 pep_c23.typed_record("unsupported", (),
                                      "Pep C23 emission requires a top-level function named main"))):
            for op, extra, want in (("tool_register", {"function": function}, "Registered"),
                                    ("tool_validate", {"testVectors": [{"arguments": arguments,
                                                                       "expect": expect,
                                                                       "semanticTarget": spec}]},
                                     "Validated"),
                                    ("tool_activate", {}, "Active")):
                resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": op,
                                     "tool": tool, "document": document, "revision": revision,
                                     **extra})
                require(resp, "status", want, f"{op} {tool}")

        payload = PROGRAM.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "wrap-043",
                               "bytes": list(payload)})
        status = target.get("status")
        gate.row("W0:host-valid", status == "valid",
                 f"open_bytes status={status} "
                 f"{[d.get('code') for d in (target.get('diagnostics') or [])][:4]}")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pf = fm(parsed)
        nodes = pf["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        labels = [helper.nval(n, "text") for n in nodes if helper.nval(n, "kind") == "function"]

        reports, sliced = {}, {}
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            chunk_nodes = index.nodes_for(sorted(index.subtree(int(helper.nval(node, "id")))))
            other = [s for s in sigs if s["name"] != label]
            sl = {"type": "ParserProgress", "fields": [
                {"name": k, "value": ({"type": "List[FlatAstNode]",
                                       "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                      if k == "nodes" else pf[k])} for k in pf]}
            chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sl,
                                              {"type": "List[CheckedFunction]",
                                               "value": [helper.checked_fn_value(s) for s in other]},
                                              {"type": "List[ResolvedSignature]",
                                               "value": [helper.resolved_sig_value(s) for s in other]},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
            if chk.get("outcome") != "ok":
                gate.row(f"W:chunk:{label}", False, f"ERROR {(chk.get('error') or {}).get('code')}")
                continue
            rpt = fm(chk["result"])
            calls = rpt.get("calls", {}).get("value") or []
            codes = [fm(x).get("code", {}).get("value")
                     for x in (rpt.get("diagnostics", {}).get("value") or [])]
            gate.row(f"W:chunk:{label}", rpt["status"]["value"] == "valid",
                     f"status={rpt['status']['value']} call_facts={len(calls)} {codes[:3]}")
            if rpt["status"]["value"] == "valid":
                reports[label] = chk["result"]
                sliced[label] = sl

        if len(reports) == len(labels):
            def invoke(tool, arguments, what):
                resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                     "op": "tool_invoke", "tool": tool, "arguments": arguments,
                                     "semanticTarget": sem})
                if resp.get("outcome") != "ok":
                    err = resp.get("error") or {}
                    raise RuntimeError(f"{what}: {err.get('code')} {err.get('message', '')[:140]}")
                ef = fm(resp["result"])
                if ef["status"]["value"] != "emitted":
                    raise RuntimeError(f"{what}: {ef['diagnostic']['value'][:180]}")
                return "".join(p["value"] for p in ef["sourceParts"]["value"])

            try:
                first = labels[0]
                header = invoke("pep-c23-section", [sliced[first], reports[first],
                                                    typed("Str", "header")], "header")
                units = ""
                for label in labels:
                    units += invoke("pep-c23-unit", [sliced[label], reports[label], typed("Int", 0)],
                                    f"unit {label}")
                epilogue = invoke("pep-c23-section", [sliced["main"], reports["main"],
                                                      typed("Str", "main")], "epilogue")
                c_source = header + units + epilogue
                gate.row("W3:all-units-emit", True, f"generator C = {len(c_source)} bytes")
            except RuntimeError as error:
                gate.row("W3:all-units-emit", False, f"FIRST REFUSAL {error}")
        else:
            gate.row("W3:all-units-emit", False,
                     f"cannot emit: chunks not all valid ({sorted(reports)} of {labels})")
    finally:
        session.close()

    emitted = {}
    if c_source:
        gen_c = BUILD / "wrap043_generator.c"
        gen_c.write_text(c_source, encoding="utf-8", newline="\n")
        gen_exe = BUILD / "wrap043_generator.exe"
        built = subprocess.run([str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall", "-Wextra",
                                "-Wpedantic", "-Werror", "-O2", str(gen_c), "-o", str(gen_exe)],
                               capture_output=True, text=True, check=False)
        gate.row("W4:generator-builds", built.returncode == 0, built.stderr.strip()[:200] or "clean")
        if built.returncode == 0:
            for tag in ("A", "B"):
                ran = subprocess.run([str(gen_exe), str(FX / f"input_{tag.lower()}.txt")],
                                     capture_output=True, text=True, check=False)
                emitted[tag] = ran.stdout
                (BUILD / f"wrap043_out_{tag}.c").write_text(ran.stdout, encoding="utf-8", newline="\n")
                gate.row(f"W5:generator-{tag}", ran.returncode == 0 and ran.stdout.strip() != "",
                         f"exit={ran.returncode} bytes={len(ran.stdout)}")
            gate.row("D3:generated-C-differs", emitted.get("A") != emitted.get("B"),
                     f"A={hashlib.sha256((emitted.get('A') or '').encode()).hexdigest()[:10]} "
                     f"B={hashlib.sha256((emitted.get('B') or '').encode()).hexdigest()[:10]}")
            outs = {}
            for tag in ("A", "B"):
                for comp, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                    exe = BUILD / f"wrap043_out_{tag}_{comp}.exe"
                    cc = subprocess.run([str(pep_c23.compiler_path(comp)), *extra, "-Wall", "-Wextra",
                                         "-Wpedantic", "-Werror", "-O2",
                                         str(BUILD / f"wrap043_out_{tag}.c"), "-o", str(exe)],
                                        capture_output=True, text=True, check=False)
                    gate.row(f"D4:generated-{tag}-{comp}", cc.returncode == 0,
                             cc.stderr.strip()[:200] or "clean")
                    if cc.returncode == 0:
                        rr = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
                        outs[(tag, comp)] = rr.stdout.strip()
            if outs:
                gate.row("D5:outputs-differ", len(set(outs.values())) > 1, f"outputs={outs}")

    _report(gate, as_json, emitted)
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json, emitted):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "INPUT-DEPENDENT" if ok else "STILL BLOCKED",
                          "checks": gate.rows, "emitted": emitted}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<28} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("wrapper variant:", "INPUT-DEPENDENT C PRODUCED" if ok else f"STILL BLOCKED {failed}")
        for tag in ("A", "B"):
            if emitted.get(tag):
                print(f"\n--- generated C from input {tag} ---\n{emitted[tag]}")


if __name__ == "__main__":
    sys.exit(main())