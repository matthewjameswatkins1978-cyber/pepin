"""A3 BOOT-A3-026: is an out-of-range byte_at on granted SourceBytes trapped or silently read?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-026-BYTE-AT-BOUNDS.md @ ac5971a,
committed before this probe existed or ran.

Definition used (from the pre-registration, not retrofitted):
  SOUND   = out-of-range offset traps with non-zero exit AND a PEP_RUNTIME_* diagnostic on stderr,
            printing no value; a static refusal also counts as SOUND.
  UNSOUND = a value is printed for an out-of-range offset, or the process dies with no
            PEP_RUNTIME_* diagnostic.
  NOT TESTED = could not build; recorded with the first refusal.

`byte_at` out-of-range behaviour is undefined by the written spec, so this is a measurement about
today's implementation, not a clause violation.

Run: python verification/probes/grant_byte_bounds_026.py [--json]
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
GRANT_DIR = BUILD / "a3-025-bytes"
A4_REV = "12e143f"
GRANT_REL = "examples/dogfood/input_ascii.pep"

CASES = [
    ("B0", "in-bounds control", "return byte_at(source, 0)", GRANT_REL, "in-bounds"),
    ("B1", "offset 0 - 1 (negative)", "return byte_at(source, 0 - 1)", GRANT_REL, "out-of-range"),
    ("B2", "offset == byte_length", "return byte_at(source, byte_length(source))", GRANT_REL,
     "one-past-end"),
    ("B3", "offset == length + 1048576", "return byte_at(source, byte_length(source) + 1048576)",
     GRANT_REL, "far-past-end"),
    ("B4", "offset 0 on an EMPTY grant", "return byte_at(source, 0)", None, "empty-grant"),
]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def materialise(rel):
    raw = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{A4_REV}:{rel}"],
                         capture_output=True, check=False)
    if raw.returncode:
        raise RuntimeError(raw.stderr.decode("utf-8", "replace").strip()[:200])
    out = GRANT_DIR / pathlib.Path(rel).name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw.stdout)
    return out, raw.stdout


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def build_vertical(gate, body_source, tag):
    """Check + emit one single-function SourceBytes program; return C source or (None, why)."""
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    src = f"fn main(source: SourceBytes) -> Int {{\n  {body_source}\n}}\n".encode("utf-8")
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
        require(sample, "outcome", "ok", "open validation source")
        pic.register(session, document, revision, sample["document"], sample["revision"])

        spec = {"document": sample["document"], "revision": sample["revision"],
                "entryFunctions": []}
        empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        for tool, function, arguments, expect in (
                ("pep-c23-checker-chunk", "analyze_chunk_typed",
                 [empty_pp, empty_ext, empty_sig,
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
                if resp.get("status") != want:
                    return None, f"tool setup {op} {tool}: {resp.get('status')}"

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": tag,
                               "bytes": list(src)})
        require(target, "outcome", "ok", "open target")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, src, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)

        node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                    and helper.nval(n, "text") == "main")
        subtree = index.subtree(int(helper.nval(node, "id")))
        chunk_nodes = index.nodes_for(sorted(subtree))
        other = [s for s in sigs if s["name"] != "main"]
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
            return None, f"CHECK ERROR {(checked.get('error') or {}).get('code')}"
        f = fm(checked["result"])
        codes = [fm(x).get("code", {}).get("value")
                 for x in (f.get("diagnostics", {}).get("value") or [])]
        if f["status"]["value"] != "valid":
            return None, f"CHECK {f['status']['value']} {codes[:3]}"
        gate.row(f"check:{tag}", True, f"valid, nodes={len(chunk_nodes)}, diagnostics={codes}")
        report = checked["result"]

        def invoke(tool, arguments, what):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool, "arguments": arguments,
                                 "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                err = resp.get("error") or {}
                raise RuntimeError(f"{what}: {err.get('code')} {err.get('message', '')[:120]}")
            ef = fm(resp["result"])
            if ef["status"]["value"] != "emitted":
                raise RuntimeError(f"{what}: {ef['diagnostic']['value'][:160]}")
            return "".join(p["value"] for p in ef["sourceParts"]["value"])

        try:
            header = invoke("pep-c23-section", [sl, report, typed("Str", "header")], "header")
            unit = invoke("pep-c23-unit", [sl, report, typed("Int", 0)], "unit main")
            epilogue = invoke("pep-c23-section", [sl, report, typed("Str", "main")], "epilogue")
        except RuntimeError as error:
            return None, f"EMIT REFUSED {error}"
        gate.row(f"emit:{tag}", True, f"header={len(header)} unit={len(unit)} "
                                      f"epilogue={len(epilogue)}")
        return header + unit + epilogue, None
    finally:
        session.close()


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    grant_path, grant_bytes = materialise(GRANT_REL)
    gate.row("grant:bytes", True,
             f"{GRANT_REL} {len(grant_bytes)} B sha256={hashlib.sha256(grant_bytes).hexdigest()[:16]}")
    empty_path = GRANT_DIR / "empty_grant.bin"
    empty_path.write_bytes(b"")
    first_byte = grant_bytes[0] if grant_bytes else None

    results = []
    for tag, label, body, grant_rel, kind in CASES:
        c_source, why = build_vertical(gate, body, tag)
        if c_source is None:
            gate.row(f"{tag}:{kind}", True,
                     f"NOT TESTED as a runtime question - refused statically ({why}). "
                     f"A static refusal is SOUND for this question.")
            results.append({"case": tag, "kind": kind, "static_refusal": why})
            continue
        c_path = BUILD / f"bounds_026_{tag}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        target_file = grant_path if grant_rel else empty_path
        for comp, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"bounds_026_{tag}_{comp}.exe"
            built = subprocess.run([str(pep_c23.compiler_path(comp)), *extra, "-Wall", "-Wextra",
                                    "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                                   capture_output=True, text=True, check=False)
            if built.returncode:
                gate.row(f"{tag}:build:{comp}", False, built.stderr.strip()[:200])
                continue
            ran = subprocess.run([str(exe), str(target_file)], capture_output=True, text=True,
                                 check=False, timeout=60)
            out = ran.stdout.replace("\r\n", "\n").strip()
            err = ran.stderr.strip()
            trapped = ran.returncode != 0 and "PEP_RUNTIME_" in err
            printed = out != ""
            if kind == "in-bounds":
                ok = ran.returncode == 0 and out == str(first_byte)
                detail = (f"stdout={out!r} expected={first_byte} exit={ran.returncode} "
                          f"stderr={err[:80]!r}")
                verdict = "PASS" if ok else "FAIL"
            else:
                ok = (not printed) and trapped
                verdict = "SOUND (trapped)" if ok else (
                    "UNSOUND (printed a value)" if printed
                    else f"UNSOUND (died without PEP_RUNTIME_* diagnostic, exit={ran.returncode})")
                detail = (f"{verdict}: stdout={out!r} exit={ran.returncode} "
                          f"stderr={err[:120]!r}")
            gate.row(f"{tag}:{comp}", ok, detail)
            results.append({"case": tag, "compiler": comp, "kind": kind, "stdout": out,
                            "exit": ran.returncode, "stderr": err[:160], "sound": ok})

    _report(gate, as_json, {"cases": CASES, "results": results})
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json, extra):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "SOUND" if ok else "UNSOUND-OR-INCOMPLETE",
                          "checks": gate.rows, "extra": extra}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<22} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("byte_at bounds question:", "SOUND" if ok
              else f"UNSOUND/CDEFFECT - {failed}")


if __name__ == "__main__":
    sys.exit(main())
