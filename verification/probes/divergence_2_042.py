"""A3 BOOT-A3-042: DIVERGENCE-2 - does a Pep program emit INPUT-DEPENDENT C23?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-042-DIVERGENCE-2.md @ 40fa4bf,
committed before this probe existed or ran.

The generator is an ordinary Pep program with a granted SourceBytes entry. Its stdout IS the generated
C. Two unseen inputs must produce DIFFERENT C text, and both must compile under strict Clang AND GCC
and run to different results. That is the floor a compiler must stand on; every Pep program verified so
far emits input-invariant C instead.

CAPABILITY PROBE, NOT A COMPILER: the generated C is a fixed template with one variable substring. It
proves input-dependent valid C23 is achievable, and nothing about lexing/parsing/checking.

Run: python verification/probes/divergence_2_042.py [--json]
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
INPUT_A = FX / "input_a.txt"
INPUT_B = FX / "input_b.txt"

# Each say() adds a newline; the C is arranged so newlines fall between tokens.
# V1 refused: "say lowers only string literals, Str parameters, Str locals and Str fields"
# (measured). V2 binds the slice to a local first, which is on that allowed list.
GEN_DIRECT = (
    'fn main(source: SourceBytes) -> Int {\n'
    '  say(utf8_slice(source, 0, 3))\n'
    '  return 0\n'
    '}\n'
)
GEN = (
    'fn main(source: SourceBytes) -> Int {\n'
    '  var part = utf8_slice(source, 0, 3)\n'
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


def build_generator(gate):
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    session = Session()
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

        payload = GEN.encode("utf-8")
        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "div2",
                               "bytes": list(payload)})
        if target.get("outcome") != "ok":
            gate.row("D1:host-valid", False, f"open failed: {(target.get('error') or {}).get('code')}")
            return None
        status = target.get("status")
        codes = [d.get("code") for d in (target.get("diagnostics") or [])][:4]
        gate.row("D1:host-valid", status == "valid", f"open_bytes status={status} {codes}")
        if status != "valid":
            return None
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pf = fm(parsed)
        nodes = pf["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                    and helper.nval(n, "text") == "main")
        chunk_nodes = index.nodes_for(sorted(index.subtree(int(helper.nval(node, "id")))))
        sl = {"type": "ParserProgress", "fields": [
            {"name": k, "value": ({"type": "List[FlatAstNode]",
                                   "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                  if k == "nodes" else pf[k])} for k in pf]}
        chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                            "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                            "arguments": [sl, {"type": "List[CheckedFunction]", "value": []},
                                          {"type": "List[ResolvedSignature]", "value": []},
                                          {"type": "List[ResolvedTypeDecl]", "value": []},
                                          {"type": "Bool", "value": True}],
                            "semanticTarget": sem})
        if chk.get("outcome") != "ok" or fm(chk["result"])["status"]["value"] != "valid":
            gate.row("D2:emits", False, f"chunk check failed: {chk.get('error')}")
            return None

        rpt = fm(chk["result"])
        call_facts = rpt.get("calls", {}).get("value") or []
        fn_facts = rpt.get("functions", {}).get("value") or []
        gate.row("diag:call-facts", True,
                 f"chunk report carries {len(call_facts)} call fact(s) and {len(fn_facts)} "
                 f"function fact(s); calleeIds="
                 f"{[fm(c).get('calleeId', {}).get('value') for c in call_facts]}")

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
            header = invoke("pep-c23-section", [sl, chk["result"], typed("Str", "header")], "header")
            unit = invoke("pep-c23-unit", [sl, chk["result"], typed("Int", 0)], "unit")
            epilogue = invoke("pep-c23-section", [sl, chk["result"], typed("Str", "main")], "epilogue")
        except RuntimeError as error:
            gate.row("D2:emits", False, f"FIRST REFUSAL {error}")
            return None
        gate.row("D2:emits", True, f"generator C = {len(header) + len(unit) + len(epilogue)} bytes")
        return header + unit + epilogue
    finally:
        session.close()


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    BUILD.mkdir(parents=True, exist_ok=True)
    c_source = build_generator(gate)
    if c_source is None:
        _report(gate, as_json, None)
        return 1

    gen_c = BUILD / "div2_generator.c"
    gen_c.write_text(c_source, encoding="utf-8", newline="\n")
    gen_exe = BUILD / "div2_generator.exe"
    built = subprocess.run([str(pep_c23.compiler_path("clang")), "-std=c23", "-Wall", "-Wextra",
                            "-Wpedantic", "-Werror", "-O2", str(gen_c), "-o", str(gen_exe)],
                           capture_output=True, text=True, check=False)
    gate.row("D2b:generator-builds", built.returncode == 0, built.stderr.strip()[:200] or "clean")
    if built.returncode != 0:
        _report(gate, as_json, None)
        return 1

    emitted = {}
    for tag, path in (("A", INPUT_A), ("B", INPUT_B)):
        ran = subprocess.run([str(gen_exe), str(path)], capture_output=True, text=True, check=False)
        out = ran.stdout
        emitted[tag] = out
        (BUILD / f"div2_out_{tag}.c").write_text(out, encoding="utf-8", newline="\n")
        gate.row(f"run:generator-{tag}", ran.returncode == 0 and out.strip() != "",
                 f"exit={ran.returncode} stderr={ran.stderr.strip()[:80]!r} "
                 f"sha256={hashlib.sha256(out.encode()).hexdigest()[:12]} bytes={len(out)}")

    differ = emitted.get("A") != emitted.get("B")
    gate.row("D3:generated-C-differs", differ,
             f"A sha={hashlib.sha256((emitted.get('A') or '').encode()).hexdigest()[:12]} "
             f"B sha={hashlib.sha256((emitted.get('B') or '').encode()).hexdigest()[:12]}")

    outputs = {}
    for tag in ("A", "B"):
        c_file = BUILD / f"div2_out_{tag}.c"
        for comp, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"div2_out_{tag}_{comp}.exe"
            cc = subprocess.run([str(pep_c23.compiler_path(comp)), *extra, "-Wall", "-Wextra",
                                 "-Wpedantic", "-Werror", "-O2", str(c_file), "-o", str(exe)],
                                capture_output=True, text=True, check=False)
            gate.row(f"D4:generated-{tag}-compiles-{comp}", cc.returncode == 0,
                     cc.stderr.strip()[:220] or "clean")
            if cc.returncode == 0:
                rr = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
                outputs[(tag, comp)] = rr.stdout.strip()
                gate.row(f"D5:generated-{tag}-runs-{comp}", rr.returncode == 0,
                         f"stdout={rr.stdout.strip()!r} exit={rr.returncode}")

    if outputs:
        distinct = len(set(outputs.values())) > 1
        gate.row("D5:outputs-differ", distinct, f"outputs={outputs}")

    _report(gate, as_json, emitted)
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json, emitted):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "INPUT-DEPENDENT" if ok else "NOT DEMONSTRATED",
                          "checks": gate.rows, "emitted": emitted}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<34} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("DIVERGENCE-2:", "INPUT-DEPENDENT C PRODUCED" if ok else f"NOT DEMONSTRATED {failed}")
        if emitted:
            for tag in ("A", "B"):
                print(f"\n--- generated C from input {tag} ---\n{emitted.get(tag, '')}")


if __name__ == "__main__":
    sys.exit(main())