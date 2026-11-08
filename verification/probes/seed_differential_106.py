#!/usr/bin/env python3
"""A3 reserve R3: seed-vs-emitted semantic differential (verification/probes).

Compares what the SEED evaluates against what the EMITTED C computes, for the same
expression. That is a differential against an independent implementation, which is
stronger than comparing emitted C to my own expectations.

Placement differs by necessity and this is the crux of the method:
  - the seed executes only TOP-LEVEL statements (`exec_stmts [] [] c.tops`); it never
    calls `main`, so a function-only program produces nothing (BOOT-A3-105).
  - the emitter requires a top-level `main` and refuses without one.
So each case supplies two sources that differ ONLY in where the expression lives. The
comparison is of values, not of code.

Also: a cross-chunk call as an argument to a builtin (`say(int_text(f(41)))`) is not
lowered today, so the emitted side must hoist into a `let` first. That is recorded in
each case rather than hidden.

  PEPIN_SEED_ROOT=<worktree with built seed>
  PEPIN_GATE_ROOT=<worktree whose emitter can emit these fixtures>

Exit 0 only when every case agrees.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
SEED = pathlib.Path(os.environ.get("PEPIN_SEED_ROOT") or PROBE_ROOT).resolve()
GATE = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(GATE))
sys.path.insert(0, str(GATE / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

HELPERS = "fn a3_double(n: Int) -> Int {\n  return n * 2\n}\n"

# (name, seed_source, emit_source, note)
# The emitted epilogue echoes main's return value as a final line; that line is
# stripped and ASSERTED to equal 0 so a change in epilogue shape fails loudly.
CASES = [
    ("cross-chunk arithmetic", 
     HELPERS + 'say(int_text(a3_double(21) + 1))\n',
     HELPERS + 'fn main() -> Int {\n  let v = a3_double(21) + 1\n  say(int_text(v))\n  return 0\n}\n',
     "emitted side hoists the cross-chunk call into a let (builtin-of-call is not lowered)"),
    ("negative integer",
     'say(int_text(7 - 10))\n',
     'fn main() -> Int {\n  let v = 7 - 10\n  say(int_text(v))\n  return 0\n}\n',
     ""),
    ("truncating division",
     'say(int_text(1 / 3))\n',
     'fn main() -> Int {\n  let v = 1 / 3\n  say(int_text(v))\n  return 0\n}\n',
     ""),
    ("string concat",
     'say(str_concat("ab", "cd"))\n',
     'fn main() -> Int {\n  say(str_concat("ab", "cd"))\n  return 0\n}\n',
     ""),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def seed_run(source):
    with tempfile.NamedTemporaryFile("w", suffix=".pep", delete=False,
                                     encoding="utf-8", newline="\n") as handle:
        handle.write(source)
        path = handle.name
    try:
        run = subprocess.run(["pwsh", "-NoProfile", "-File", str(SEED / "pep.ps1"),
                              "run", path], cwd=str(SEED), capture_output=True,
                             text=True, check=False)
        return run.stdout.replace("\r\n", "\n").rstrip("\n"), run.returncode, run.stderr.strip()
    finally:
        os.unlink(path)


def emit_run(session, source, workdir, bundle_revision):
    """Emit one program through the sectional-free unit path and run it natively."""
    helper = load("ch", GATE / "tests" / "chunk_helper.py")
    pic = load("pic", GATE / "tests" / "probe_integration_case.py")
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "r3",
                           "bytes": list(payload)})
    if target.get("status") != "valid":
        return None, f"host analysis {target.get('status')}", ""
    sem = {"document": target["document"], "revision": target["revision"],
           "entryFunctions": ["main"]}
    # parse_target needs the BUNDLE revision (the emitter sources), not the
    # target document revision - the parser cursor is keyed to the tool revision.
    parsed = parse_target(session, payload, target, bundle_revision)
    pf = fm(parsed)
    nodes = pf["nodes"]["value"]
    index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
    sigs = helper.fetch_all_sigs(session, parsed, bundle_revision, sem)
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
            return None, f"chunk {label} {(chk.get('error') or {}).get('code')}", ""
        reports[label] = chk["result"]
        sliced[label] = sl

    def invoke(tool, arguments, what):
        resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": tool, "arguments": arguments,
                             "semanticTarget": sem})
        if resp.get("outcome") != "ok":
            raise RuntimeError(f"{what}: {(resp.get('error') or {}).get('code')}")
        ef = fm(resp["result"])
        if ef["status"]["value"] != "emitted":
            raise RuntimeError(f"{what}: {ef['diagnostic']['value'][:160]}")
        return "".join(p["value"] for p in ef["sourceParts"]["value"])

    pieces = ["".join([invoke("pep-c23-section",
                              [sliced[labels[0]], reports[labels[0]], typed("Str", "header")],
                              "header")])]
    for label in labels:
        try:
            pieces.append(invoke("pep-c23-unit", [sliced[label], reports[label], typed("Int", 0)],
                                 f"unit {label}"))
        except RuntimeError as error:
            return None, str(error), ""
    pieces.append(invoke("pep-c23-section",
                         [sliced["main"], reports["main"], typed("Str", "main")], "epilogue"))
    c_path = workdir / "r3.c"
    c_path.write_text("".join(pieces), encoding="utf-8", newline="\n")
    outputs = {}
    for comp, std in (("clang", "-std=c23"), ("gcc", "-std=c2x")):
        exe = workdir / f"r3_{comp}.exe"
        cc = subprocess.run([str(pep_c23.compiler_path(comp)), std, "-Wall", "-Wextra",
                             "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                            capture_output=True, text=True, check=False)
        if cc.returncode != 0:
            return None, f"{comp} build failed: {cc.stderr.strip()[:120]}", ""
        run = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
        outputs[comp] = run.stdout.replace("\r\n", "\n").rstrip("\n")
    return outputs, "", ""


def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix="a3-r3-"))
    session = Session()
    bad = 0
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open bundle")
        require(opened, "status", "valid", "check bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate",
                               "bytes": []})
        picmod = load("pic", GATE / "tests" / "probe_integration_case.py")
        picmod.register(session, document, revision, sample["document"], sample["revision"])
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

        print(f"seed: {SEED}\ngate: {GATE}\n")
        for name, seed_src, emit_src, note in CASES:
            seed_out, code, err = seed_run(seed_src)
            outputs, why, _ = emit_run(session, emit_src, work, revision)
            if outputs is None:
                bad += 1
                print(f"FAIL {name:<24} emitter: {why}")
                continue
            agree = all(v == seed_out for v in outputs.values())
            # strip the epilogue's return echo and assert it is 0
            stripped = {}
            for comp, val in outputs.items():
                lines = val.split("\n") if val else []
                stripped[comp] = "\n".join(lines[:-1]) if lines else ""
            epilogue_ok = all(v.split("\n")[-1] == "0" for v in outputs.values() if v)
            agree = all(stripped[c] == seed_out for c in stripped)
            if not (agree and epilogue_ok):
                bad += 1
                print(f"FAIL {name:<24} seed={seed_out!r} clang={stripped.get('clang')!r} "
                      f"gcc={stripped.get('gcc')!r} epilogue0={epilogue_ok}")
            else:
                print(f"PASS {name:<24} both print {seed_out!r}"
                      + (f"  [{note}]" if note else ""))
        print(f"\n{len(CASES)} cases, {bad} disagreeing")
        print("SEED vs EMITTED: " + ("AGREE" if bad == 0 else "DISAGREE"))
        return 0 if bad == 0 else 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())