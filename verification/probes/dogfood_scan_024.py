"""A3 independent dogfood gate: source-scan vertical over A3's own corpus (BOOT-A3-024).

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-024-DOGFOOD-SCAN.md,
committed at a9f4314 BEFORE this probe existed or ran.

What is under test
------------------
The pinned four-function source-scan vertical:
  ascii_letter / ascii_digit / ascii_continue   (verbatim examples/pep_lexer.pep @ A1)
  main(source: SourceBytes) -> Int              counts bytes b with ascii_continue(b)

Semantics are a BYTE-CLASS COUNT: |{b : b in [0x30-0x39] | [0x41-0x5A] | [0x61-0x7A] | 0x5F}|.
Not a lexer, not a token count.

Independence
------------
Three derivations that must agree per file:
  1. HAND   - the tallies frozen in the pre-registration commit (before execution)
  2. REF    - a Python classifier over the exact on-disk bytes (no Pep, no checker, no emitter)
  3. SEED   - the Pep interpreter, given the same byte values as a literal Int list
              (`run` cannot reach source_bytes(), so the bytes are supplied by value; that
              authority boundary is labelled, not hidden)
plus the NATIVE binary under strict Clang and strict GCC.

Harness plumbing disclosure
---------------------------
The session call sequence (open bundle -> register/validate/activate chunk tools -> open_bytes
-> parse_target -> per-function chunk + emit -> assemble) follows A2's published
tests/probe_grant_lexer_chunked.py. That plumbing is reused deliberately: it is the seam's
marshalling layer, not the claim under test. The claim (which files, which values, which
negatives, which provenance) is A3's and is fixed in the pre-registration.

Run: python verification/probes/dogfood_scan_024.py [--json]
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
# ROOT is the tree UNDER TEST (defaults to this repo); the corpus always belongs to A3.
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

BUILD = ROOT / "_build"
SEED = BUILD / "a1_seed" / "pep.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"
CORPUS = PROBE_ROOT / "verification" / "fixtures" / "dogfood-scan"

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

# Frozen in the pre-registration commit (a9f4314), before any execution.
PREDICTED = {
    "scan_ascii.pep": 24,
    "scan_nonascii.pep": 26,
    "scan_empty.pep": 0,
    "scan_nul.pep": 16,
    "scan_hello.pep": 11,
    "scan_punct.pep": 0,
}
ORDER = ["scan_ascii.pep", "scan_nonascii.pep", "scan_empty.pep",
         "scan_nul.pep", "scan_hello.pep", "scan_punct.pep"]

# derivation 2: independent reference, sharing nothing with Pep.
IDENT = frozenset(list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) +
                  list(range(0x61, 0x7B)) + [0x5F])

NEGATIVE_FACTS = (
    ("facts:stripped",
     "Pep C23 cross-chunk call has no resolved call fact"),
    ("facts:severed-callee",
     "Pep C23 cross-chunk call target is missing from the checked functions"),
    ("facts:forged-arity",
     "Pep C23 cross-chunk call argument count disagrees with the checked arity"),
)


def reference_count(path):
    data = pathlib.Path(path).read_bytes()
    return sum(1 for b in data if b in IDENT)


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
        return bool(ok)


def recmap(rec):
    return {f["name"]: f["value"] for f in rec["fields"]}


def with_field(rec, name, value):
    return {"type": rec["type"], "fields": [
        ({"name": f["name"], "value": value} if f["name"] == name else f)
        for f in rec["fields"]]}


def tampered_reports(reports):
    """The three malformed/incomplete fact shapes, built from the honest main report."""
    main_report = reports["main"]
    main_fields = recmap(main_report)
    calls = json.loads(json.dumps(main_fields["calls"]["value"]))
    functions = json.loads(json.dumps(main_fields["functions"]["value"]))
    continue_sem = int(recmap(next(x for x in functions
                                   if recmap(x)["name"]["value"] == "ascii_continue"))
                       ["semanticId"]["value"])
    continue_fact = next(f for f in calls
                         if int(recmap(f)["calleeId"]["value"]) == continue_sem)
    return [
        with_field(main_report, "calls", {"type": "List[ResolvedCall]", "value": []}),
        with_field(main_report, "calls", {"type": "List[ResolvedCall]", "value": [
            with_field(continue_fact, "calleeId", typed("Int", 999999))
            if recmap(f)["syntaxId"] == recmap(continue_fact)["syntaxId"] else f
            for f in calls]}),
        with_field(main_report, "functions", {"type": "List[CheckedFunction]", "value": [
            with_field(f, "arity", typed("Int", 2))
            if recmap(f)["name"]["value"] == "ascii_continue" else f
            for f in functions]}),
    ]


def emit_pipeline(build, gate):
    """Build the four-function vertical natively; return (assembled, by_name) or (None, by_name)."""
    chunk_helper_path = ROOT / "tests" / "chunk_helper.py"
    if not chunk_helper_path.is_file():
        raise RuntimeError("no tests/chunk_helper.py in this tree")

    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    pfc = load("pfc", ROOT / "tests" / "probe_function_closure.py")
    helper = load("ch", chunk_helper_path)

    lexer_text = LEXER.read_text(encoding="utf-8")
    _, functions = pfc.split_source(lexer_text)
    by_name = dict(functions)
    fixture = (by_name["ascii_letter"] + "\n" + by_name["ascii_digit"] + "\n" +
               by_name["ascii_continue"] + "\n" + SCAN_MAIN)

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
                               "name": "dogfood-scan-a3", "bytes": list(payload)})
        require(target, "outcome", "ok", "open scan vertical")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)

        labels = ["ascii_letter", "ascii_digit", "ascii_continue", "main"]
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
                gate.row(f"chunk:{label}", False,
                         f"ERROR {(checked.get('error') or {}).get('code')}")
                continue
            f = fm(checked["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            gate.row(f"chunk:{label}", f["status"]["value"] == "valid",
                     f"nodes={len(chunk_nodes)} status={f['status']['value']} {codes[:2]}")
            if f["status"]["value"] != "valid":
                continue
            reports[label] = checked["result"]
            sliced[label] = sl

        if len(reports) != len(labels):
            gate.row("emit:all", False, f"only {sorted(reports)} checked valid")
            return None, by_name

        def invoke(tool, arguments, what):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool,
                                 "arguments": arguments, "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                raise RuntimeError(f"{what}: {(resp.get('error') or {}).get('code')}")
            efields = fm(resp["result"])
            if efields["status"]["value"] != "emitted":
                raise RuntimeError(f"{what}: status={efields['status']['value']} "
                                   f"{efields['diagnostic']['value'][:160]}")
            return "".join(p["value"] for p in efields["sourceParts"]["value"])

        header = invoke("pep-c23-section",
                        [sliced["ascii_letter"], reports["ascii_letter"],
                         typed("Str", "header")], "header")
        units = ""
        emitted = []
        for label in labels:
            units += invoke("pep-c23-unit",
                            [sliced[label], reports[label], typed("Int", 0)],
                            f"unit {label}")
            emitted.append(label)
        prototypes = "".join(
            invoke("pep-c23-section",
                   [sliced[label], reports[label], typed("Str", "prototypes")],
                   f"prototypes {label}") for label in labels)
        epilogue = invoke("pep-c23-section",
                          [sliced["main"], reports["main"], typed("Str", "main")],
                          "epilogue")
        gate.row("emit:all", True,
                 f"emitted {emitted} header={len(header)} prototypes={len(prototypes)} "
                 f"units={len(units)} epilogue={len(epilogue)}")
        grant = "pep_source_data" in epilogue
        gate.row("epilogue:grant-wrapper", grant,
                 "pep_source_data present (real file read by the binary)"
                 if grant else "no grant wrapper")

        # ---- malformed / incomplete fact cases, same emit entry -------------
        def unit_refusal(report):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-unit",
                                 "arguments": [sliced["main"], report, typed("Int", 0)],
                                 "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                error = resp.get("error") or {}
                return None, f"{error.get('code')} {error.get('message', '')}".strip()
            efields = fm(resp["result"])
            if efields["status"]["value"] != "emitted":
                return None, str(efields["diagnostic"]["value"])
            return "".join(p["value"] for p in efields["sourceParts"]["value"]), None

        for (name, needle), tampered in zip(NEGATIVE_FACTS, tampered_reports(reports)):
            piece, why = unit_refusal(tampered)
            if piece is not None:
                gate.row(name, False, "FAIL: expected refusal, got emission")
            elif needle not in why:
                gate.row(name, False, f"FAIL: refusal {why!r} lacks {needle!r}")
            else:
                gate.row(name, True, needle)

        # ---- N8: revision binding. An honest report must not be accepted on another target.
        other_target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "dogfood-scan-a3-stale",
                                     "bytes": list(b"fn main() -> Int { return 0 }\n")})
        require(other_target, "outcome", "ok", "open second target for stale check")
        stale_sem = {"document": other_target["document"],
                     "revision": other_target["revision"], "entryFunctions": ["main"]}
        stale = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_invoke", "tool": "pep-c23-unit",
                              "arguments": [sliced["main"], reports["main"], typed("Int", 0)],
                              "semanticTarget": stale_sem})
        stale_text = json.dumps(stale)
        gate.row("facts:stale-revision",
                 stale.get("outcome") != "ok" and "PEP_STALE_REVISION" in stale_text,
                 "PEP_STALE_REVISION" if "PEP_STALE_REVISION" in stale_text
                 else stale_text[:220])

        assembled = {"docorder": header + units + epilogue,
                     "protofirst": header + prototypes + units + epilogue}
        return assembled, by_name
    finally:
        session.close()


def oracle_count(seed, by_name, payload, out_path):
    """Derivation 3: the Pep interpreter over the same byte VALUES (literal Int list)."""
    oracle = "".join(by_name[n] + "\n"
                     for n in ("ascii_letter", "ascii_digit", "ascii_continue"))
    # The parameter supplies the expected element type, so the empty file is expressible:
    # `let bytes = []` is refused by the seed itself with PEP_EMPTY_LIST_NEEDS_TYPE.
    oracle += ("fn count_from(bytes: List[Int]) -> Int {\n"
               "  var n = 0\n"
               "  for b in bytes { if ascii_continue(b) { n = n + 1 } else {} }\n"
               "  return n\n"
               "}\n")
    oracle += "say(int_text(count_from([" + ", ".join(str(b) for b in payload) + "])))\n"
    out_path.write_text(oracle, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(seed), "run", str(out_path)],
                         capture_output=True, text=True, check=False)
    if ran.returncode:
        return None, ran.stderr.strip()[:200]
    return ran.stdout.replace("\r\n", "\n").strip(), None


def main():
    as_json = "--json" in sys.argv
    gate = Gate()

    if not SEED.is_file():
        built = BUILD / "ocaml" / "pep.exe"
        if not built.is_file():
            print("FAIL: no seed binary; run .\\pep.ps1 run examples/hello.pep first")
            return 1
        SEED.parent.mkdir(parents=True, exist_ok=True)
        SEED.write_bytes(built.read_bytes())
        gate.row("seed:materialised", True, f"copied {built} -> {SEED} (same merged tree)")

    assembled, by_name = emit_pipeline(BUILD, gate)
    if assembled is None:
        _report(gate, as_json, None)
        return 1

    binaries = {}
    for order, c_source in assembled.items():
        c_path = BUILD / f"dogfood_scan_024_{order}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"dogfood_scan_024_{order}_{name}.exe"
            built = subprocess.run(
                [str(pep_c23.compiler_path(name)), *extra,
                 "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                 str(c_path), "-o", str(exe)],
                capture_output=True, text=True, check=False)
            gate.row(f"build:{order}:{name}", built.returncode == 0,
                     (built.stderr.strip()[:300] or "clean"))
            if built.returncode == 0:
                binaries[f"{order}:{name}"] = exe

    # ---- the corpus: three derivations + two compilers per file -------------
    for file_name in ORDER:
        path = CORPUS / file_name
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        hand = PREDICTED[file_name]
        ref = reference_count(path)
        gate.row(f"reference:{file_name}", ref == hand,
                 f"hand={hand} python_reference={ref} sha256={digest[:16]} bytes={len(payload)}")
        seed_value, seed_error = oracle_count(
            SEED, by_name, payload, BUILD / f"dogfood_scan_024_oracle_{file_name}.pep")
        gate.row(f"seed:{file_name}", seed_value is not None and seed_value == str(hand),
                 f"seed={seed_value} hand={hand}" if seed_error is None
                 else f"seed error {seed_error}")
        for key, exe in binaries.items():
            ran = subprocess.run([str(exe), str(path)], capture_output=True, text=True,
                                 check=False)
            got = ran.stdout.replace("\r\n", "\n").strip()
            gate.row(f"native:{key}:{file_name}",
                     ran.returncode == 0 and got == str(hand) and not ran.stderr.strip(),
                     f"stdout={got!r} exit={ran.returncode} "
                     f"stderr={ran.stderr.strip()[:80]!r} hand={hand}")

    # ---- real files from the pinned tree (REFERENCE-DERIVED, not pre-registered)
    # These are the repository's own sources, not A3 fixtures. Their expected values come
    # from the independent Python classifier, which is disclosed rather than smuggled in as
    # a hand prediction.
    for rel in ("examples/hello.pep", "examples/point_sum.pep", "examples/pep_lexer.pep"):
        path = ROOT / rel
        if not path.is_file():
            gate.row(f"repo:{rel}", False, "absent in the tree under test")
            continue
        expected = reference_count(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for key, exe in binaries.items():
            ran = subprocess.run([str(exe), str(path)], capture_output=True, text=True,
                                 check=False)
            got = ran.stdout.replace("\r\n", "\n").strip()
            gate.row(f"repo:{key}:{rel}",
                     ran.returncode == 0 and got == str(expected),
                     f"stdout={got!r} exit={ran.returncode} "
                     f"stderr={ran.stderr.strip()[:90]!r} reference={expected} "
                     f"sha256={digest[:16]}")

    # ---- honest usable scale: how large a real file can this vertical scan? --
    if binaries:
        exe = binaries["docorder:clang"]
        last_ok, first_refusal = None, None
        for size in (1024, 4096, 16384, 65536, 131072, 262144, 524288, 1048576):
            probe_path = BUILD / f"dogfood_scan_024_scale_{size}.pep"
            probe_path.write_bytes(b"A" * size)   # every byte is identifier-class
            ran = subprocess.run([str(exe), str(probe_path)], capture_output=True,
                                 text=True, check=False)
            got = ran.stdout.replace("\r\n", "\n").strip()
            if ran.returncode == 0 and got == str(size):
                last_ok = size
            else:
                first_refusal = (size, ran.returncode, ran.stderr.strip()[:120])
                break
        gate.row("scale:largest-scanned", last_ok is not None,
                 f"largest all-identifier file fully scanned = {last_ok} bytes; "
                 f"first refusal = {first_refusal}")

    # ---- metamorphic: one binary, six files, six distinct answers -----------
    if binaries:
        probe_exe = binaries["docorder:clang"]
        seen = []
        for file_name in ORDER:
            ran = subprocess.run([str(probe_exe), str(CORPUS / file_name)],
                                 capture_output=True, text=True, check=False)
            seen.append(ran.stdout.replace("\r\n", "\n").strip())
        gate.row("metamorphic:one-binary-six-files",
                 seen == [str(PREDICTED[f]) for f in ORDER],
                 f"answers={seen} (a constant-printing build fails here)")

    # ---- path negatives (contract measured from the generated epilogue) -----
    if binaries:
        exe = binaries["docorder:clang"]
        missing = subprocess.run([str(exe), str(BUILD / "does-not-exist-024.pep")],
                                 capture_output=True, text=True, check=False)
        gate.row("negative:missing-file",
                 missing.returncode != 0 and missing.stdout.strip() == ""
                 and "PEP_RUNTIME_SOURCE_OPEN" in missing.stderr,
                 f"exit={missing.returncode} stdout={missing.stdout.strip()!r} "
                 f"stderr={missing.stderr.strip()!r}")
        directory = subprocess.run([str(exe), str(CORPUS)], capture_output=True,
                                   text=True, check=False)
        gate.row("negative:directory",
                 directory.returncode != 0 and directory.stdout.strip() == ""
                 and directory.stderr.strip() != "",
                 f"exit={directory.returncode} stdout={directory.stdout.strip()!r} "
                 f"stderr={directory.stderr.strip()!r}")
        noz = subprocess.run([str(exe)], capture_output=True, text=True, check=False)
        gate.row("negative:no-argument",
                 noz.returncode != 0 and noz.stdout.strip() == ""
                 and "PEP_RUNTIME_SOURCE_CONTEXT" in noz.stderr,
                 f"exit={noz.returncode} stdout={noz.stdout.strip()!r} "
                 f"stderr={noz.stderr.strip()!r}")

    _report(gate, as_json, {"assembled_bytes": {k: len(v) for k, v in assembled.items()},
                            "predicted": PREDICTED})
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json, extra):
    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "PROVEN" if ok else "FAIL",
                          "checks": gate.rows, "extra": extra}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<44} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("dogfood source-scan gate:", "PROVEN" if ok else f"FAIL {failed}")


if __name__ == "__main__":
    sys.exit(main())
