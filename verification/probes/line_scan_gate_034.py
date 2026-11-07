"""A3 BOOT-A3-034: independent gate of A2's claim that pepin-line-scan passes natively.

A2's receipt 47 (`codex/a2-bounded-emission@4b70c61`) claims a **FULL NATIVE PASS, 3/5/0/39** for
`examples/dogfood/pepin-line-scan.pep`. This is A4's second program, and its semantics are simple
and independently verifiable: count bytes with value 10 (LF).

A3 already measured those LF counts in BOOT-A3-031 (3/5/0/39) with a pure-Python oracle over
committed blobs, i.e. **before** this claim existed. So the correctness target here is already
pinned by an independent derivation, not by A2's numbers.

Emitter under test: blob 3f5b9582 — identical at A2's `4b70c61` and A1's integrated `4e325e0`, so
gating on A1's tree tests exactly A2's current emitter.

Note on scope: this gates A4's SECOND program. It does not touch the frozen acceptance target
(`pepin-source-scan.pep`, blob 4a44dd65), which still has no native result.

Run: python verification/probes/line_scan_gate_034.py [--json]
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
PINNED = BUILD / "a3-034-bytes"
APP_REL = "examples/dogfood/pepin-line-scan.pep"
APP_REV = os.environ.get("PEPIN_LINE_SCAN_REV", "36934a6")
APP_BLOB = "2e7235cc08755a289147af164af4f8b6d2498369"

# A3's own independently measured LF counts (BOOT-A3-031), i.e. the target, not A2's claim.
# 39 is the LF count of pepin-source-scan.pep (A4's fourth fixture), NOT of pepin-line-scan.pep:
# an earlier version of this probe carried 39 across to the wrong file and was corrected by
# measurement (native and oracle both said 32 for pepin-line-scan.pep).
EXPECTED = {
    "input_ascii.pep": 3,
    "input_nonascii.pep": 5,
    "input_empty.pep": 0,
    "pepin-source-scan.pep": 39,
    "pepin-line-scan.pep": 32,
}
ORDER = ["input_ascii.pep", "input_nonascii.pep", "input_empty.pep",
         "pepin-source-scan.pep", "pepin-line-scan.pep"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def blob(rel, rev=APP_REV):
    done = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{rev}:{rel}"],
                          capture_output=True, check=False)
    if done.returncode:
        raise RuntimeError(done.stderr.decode("utf-8", "replace").strip()[:160])
    return done.stdout


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    PINNED.mkdir(parents=True, exist_ok=True)

    app = blob(APP_REL)
    gate.row("app:pinned", len(app) == 998 and hashlib.sha256(app).hexdigest().startswith("12d4b1ab"),
             f"{len(app)} B sha256={hashlib.sha256(app).hexdigest()[:16]} rev={APP_REV}")

    fixtures = {}
    for name in ORDER:
        rel = f"examples/dogfood/{name}"
        data = blob(rel)
        path = PINNED / name
        path.write_bytes(data)
        fixtures[name] = (path, data)
        ref = data.count(10)
        gate.row(f"oracle:{name}", ref == EXPECTED[name],
                 f"expected={EXPECTED[name]} a3_oracle={ref} bytes={len(data)}")

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

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "line-scan",
                               "bytes": list(app)})
        require(target, "outcome", "ok", "open line-scan")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, app, target, revision)
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
                gate.row(f"chunk:{label}", False,
                         f"ERROR {(checked.get('error') or {}).get('code')}")
                continue
            f = fm(checked["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            gate.row(f"chunk:{label}", f["status"]["value"] == "valid",
                     f"nodes={len(chunk_nodes)} status={f['status']['value']} {codes[:2]}")
            if f["status"]["value"] == "valid":
                reports[label] = checked["result"]
                sliced[label] = sl

        if len(reports) != len(labels):
            gate.row("emit:all", False, f"only {sorted(reports)} checked valid")
            _report(gate, as_json)
            return 1

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

        first = labels[0]
        try:
            header = invoke("pep-c23-section", [sliced[first], reports[first],
                                                typed("Str", "header")], "header")
            units, emitted = "", []
            for label in labels:
                units += invoke("pep-c23-unit", [sliced[label], reports[label], typed("Int", 0)],
                                f"unit {label}")
                emitted.append(label)
            prototypes = "".join(
                invoke("pep-c23-section", [sliced[label], reports[label], typed("Str", "prototypes")],
                       f"prototypes {label}") for label in labels)
            epilogue = invoke("pep-c23-section", [sliced["main"], reports["main"],
                                                  typed("Str", "main")], "epilogue")
        except RuntimeError as error:
            gate.row("emit:all", False, f"FIRST REFUSAL {error}")
            _report(gate, as_json)
            return 1
        gate.row("emit:all", True,
                 f"emitted {emitted} units={len(units)} epilogue={len(epilogue)}")
        gate.row("epilogue:grant-wrapper", "pep_source_data" in epilogue,
                 "pep_source_data present" if "pep_source_data" in epilogue else "absent")
        assembled = {"docorder": header + units + epilogue,
                     "protofirst": header + prototypes + units + epilogue}
    finally:
        session.close()

    binaries = {}
    for order, c_source in assembled.items():
        c_path = BUILD / f"line_scan_034_{order}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"line_scan_034_{order}_{name}.exe"
            built = subprocess.run([str(pep_c23.compiler_path(name)), *extra, "-Wall", "-Wextra",
                                    "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                                   capture_output=True, text=True, check=False)
            gate.row(f"build:{order}:{name}", built.returncode == 0,
                     built.stderr.strip()[:240] or "clean")
            if built.returncode == 0:
                binaries[f"{order}:{name}"] = exe

    for name in ORDER:
        path = fixtures[name][0]
        want = EXPECTED[name]
        for key, exe in binaries.items():
            ran = subprocess.run([str(exe), str(path)], capture_output=True, text=True,
                                 check=False)
            got = ran.stdout.replace("\r\n", "\n").strip()
            gate.row(f"native:{key}:{name}",
                     ran.returncode == 0 and got == str(want) and not ran.stderr.strip(),
                     f"stdout={got!r} exit={ran.returncode} stderr={ran.stderr.strip()[:60]!r} "
                     f"expected={want}")

    if binaries:
        exe = binaries["docorder:clang"]
        seen = [subprocess.run([str(exe), str(fixtures[n][0])], capture_output=True, text=True,
                               check=False).stdout.replace("\r\n", "\n").strip() for n in ORDER]
        gate.row("metamorphic:one-binary-four-files", seen == [str(EXPECTED[n]) for n in ORDER],
                 f"answers={seen}")
        missing = subprocess.run([str(exe), str(BUILD / "absent-034.pep")],
                                 capture_output=True, text=True, check=False)
        gate.row("negative:missing-file",
                 missing.returncode != 0 and missing.stdout.strip() == ""
                 and "PEP_RUNTIME_SOURCE_OPEN" in missing.stderr,
                 f"exit={missing.returncode} stdout={missing.stdout.strip()!r} "
                 f"stderr={missing.stderr.strip()!r}")
        noz = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
        gate.row("negative:no-argument",
                 noz.returncode != 0 and noz.stdout.strip() == ""
                 and "PEP_RUNTIME_SOURCE_CONTEXT" in noz.stderr,
                 f"exit={noz.returncode} stdout={noz.stdout.strip()!r} "
                 f"stderr={noz.stderr.strip()!r}")

    _report(gate, as_json)
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "PROVEN" if ok else "FAIL", "checks": gate.rows}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<44} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("line-scan native gate:", "PROVEN" if ok else f"FAIL {failed}")


if __name__ == "__main__":
    sys.exit(main())
