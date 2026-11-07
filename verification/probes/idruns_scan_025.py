"""A3 independent gate: A4's identifier-start-run application (BOOT-A3-025).

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-025-IDRUNS.md, committed at
97404bc BEFORE this probe existed, before any run of the application, and before reading A2's
#16 receipt 6706527165.

Program under test (A4, FROZEN for this gate)
---------------------------------------------
examples/dogfood/pepin-source-scan.pep @ spec/agent4-spec-lab:12e143f
blob 4a44dd653e949258a196d247097197d7c24c1da7

    count = |{ o : ascii_letter(b[o]) and (o == 0 or not ascii_continue(b[o-1])) }|

This is an identifier-START-RUN count, still NOT a lexer and NOT tokenisation. The previous
67/67 (BOOT-A3-024, dfca7d2) certified a different program -- a whole-file byte-class counter --
and is NOT evidence for this application.

Evidence layers, kept separate
------------------------------
  1 A4 reference  : A4's own claimed numbers. Builder-side; not evidence about the compiler.
  2 A3 oracle     : read_bytes() + the three predicates in plain Python. No Pep, no checker,
                    no emitter, no seed.
  3 Seed          : the Pep interpreter, same byte VALUES via a typed List[Int] parameter.
  4 Native        : strict Clang -std=c23 and strict GCC -std=c2x, -Wall -Wextra -Wpedantic
                    -Werror -O2, both assembly orders.

A3 certifies only what layers 2-4 agree on.

Run: python verification/probes/idruns_scan_025.py [--json]
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
SEED = BUILD / "a1_seed" / "pep.exe"
APP_REL = "examples/dogfood/pepin-source-scan.pep"
APP_BLOB = "4a44dd653e949258a196d247097197d7c24c1da7"
CORPUS = PROBE_ROOT / "verification" / "fixtures" / "idruns"
# Committed blobs are LF. This machine has core.autocrlf=true and no .gitattributes, so a
# checked-out copy is CRLF and its bytes are NOT the pinned revision's bytes. A3 therefore
# materialises the committed blobs and runs the binary over exactly those bytes.
A4_REV = "12e143f"
PINNED_DIR = BUILD / "a3-025-bytes"

# Frozen in the pre-registration commit (97404bc), before any execution.
PREDICTED = {
    "idruns_digits_underscore.pep": 3,
    "idruns_utf8.pep": 5,
    "idruns_comments_strings.pep": 6,
    "idruns_nul.pep": 3,
    "idruns_nonempty_zero.pep": 0,
    "idruns_empty.pep": 0,
}
ORDER = ["idruns_digits_underscore.pep", "idruns_utf8.pep", "idruns_comments_strings.pep",
         "idruns_nul.pep", "idruns_nonempty_zero.pep", "idruns_empty.pep"]

# Input-byte hashes frozen in the pre-registration commit (97404bc).
EXPECTED_SHA256 = {
    "idruns_digits_underscore.pep": "059215ea669d6090c8da008057cf67687a617f2d5a648008ad119a41dc1f2524",
    "idruns_utf8.pep": "2117b3cb6eb5294d6b4ace73c5f3a2ed2ec959664fa77cec0c19f6506f1f8779",
    "idruns_comments_strings.pep": "56a1434654a8a929b660f80938b90015ff458dec8e4144fdb6ee57693dc47b60",
    "idruns_nul.pep": "4af7734867801e5e04eda447cef221e952e894999be5ebcd9e9ab8d7a662f934",
    "idruns_nonempty_zero.pep": "b129ce1eb164e863b0c9ec9772af9f6f0f16a4781b47b188e5585747ee51ef38",
    "idruns_empty.pep": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}

# A4's OWN claims (SPEC.md). Recorded to be checked, never as A3 predictions.
A4_CLAIMS = {
    "examples/dogfood/input_ascii.pep": 23,
    "examples/dogfood/input_nonascii.pep": 30,
    "examples/dogfood/input_empty.pep": 0,
    "examples/dogfood/pepin-source-scan.pep": 139,
}

LETTER = frozenset(list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + [0x5F])
DIGIT = frozenset(range(0x30, 0x3A))
CONTINUE = LETTER | DIGIT

NEGATIVE_FACTS = (
    ("facts:stripped", "Pep C23 cross-chunk call has no resolved call fact"),
    ("facts:severed-callee",
     "Pep C23 cross-chunk call target is missing from the checked functions"),
    ("facts:forged-arity",
     "Pep C23 cross-chunk call argument count disagrees with the checked arity"),
)


def oracle_count(path):
    """Layer 2. Independent of A4, of Pep and of every builder artefact."""
    b = pathlib.Path(path).read_bytes()
    return sum(1 for o, byte in enumerate(b)
               if byte in LETTER and (o == 0 or b[o - 1] not in CONTINUE))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialise(rel, rev=A4_REV):
    """Write the COMMITTED blob bytes to a real file and return (path, bytes)."""
    raw = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{rev}:{rel}"],
                         capture_output=True, check=False)
    if raw.returncode:
        raise RuntimeError(raw.stderr.decode("utf-8", "replace").strip()[:200])
    out = PINNED_DIR / pathlib.Path(rel).name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw.stdout)
    return out, raw.stdout


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def recmap(rec):
    return {f["name"]: f["value"] for f in rec["fields"]}


def with_field(rec, name, value):
    return {"type": rec["type"], "fields": [
        ({"name": f["name"], "value": value} if f["name"] == name else f)
        for f in rec["fields"]]}


def tampered_reports(reports, label):
    """Malformed fact shapes built from one honest report of the app's own function."""
    report = reports[label]
    fields = recmap(report)
    calls = json.loads(json.dumps(fields["calls"]["value"]))
    functions = json.loads(json.dumps(fields["functions"]["value"]))
    if not calls:
        return None
    first_call = calls[0]
    callee = int(recmap(first_call)["calleeId"]["value"])
    shapes = [with_field(report, "calls", {"type": "List[ResolvedCall]", "value": []})]
    shapes.append(with_field(report, "calls", {"type": "List[ResolvedCall]", "value": [
        with_field(first_call, "calleeId", typed("Int", 999999))
        if recmap(f)["syntaxId"] == recmap(first_call)["syntaxId"] else f
        for f in calls]}))
    target_name = next((recmap(f)["name"]["value"] for f in functions
                        if int(recmap(f)["semanticId"]["value"]) == callee), None)
    shapes.append(with_field(report, "functions", {"type": "List[CheckedFunction]", "value": [
        with_field(f, "arity", typed("Int", 9))
        if recmap(f)["name"]["value"] == target_name else f
        for f in functions]}))
    return shapes


def emit_pipeline(gate, app_path):
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    pfc = load("pfc", ROOT / "tests" / "probe_function_closure.py")

    app_bytes = pathlib.Path(app_path).read_bytes()
    app_sha = hashlib.sha256(app_bytes).hexdigest()
    blob = subprocess.run(["git", "-C", str(ROOT), "hash-object", "--no-filters",
                           str(app_path)], capture_output=True, text=True,
                          check=False).stdout.strip()
    gate.row("app:pinned-blob", blob == APP_BLOB,
             f"blob={blob} expected={APP_BLOB} sha256={app_sha[:16]} bytes={len(app_bytes)}")

    app_text = app_bytes.decode("utf-8")
    _, app_functions = pfc.split_source(app_text)
    by_name = dict(app_functions)
    gate.row("app:function-set", set(by_name) == {"ascii_letter", "ascii_digit",
                                                 "ascii_continue", "main"},
             f"functions={sorted(by_name)}")

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

        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "a4-source-scan", "bytes": list(app_bytes)})
        require(target, "outcome", "ok", "open A4 application")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, app_bytes, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)

        labels = [n for n in by_name]
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
                     f"nodes={len(chunk_nodes)} status={f['status']['value']} {codes[:3]}")
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
                raise RuntimeError(f"{what}: {(resp.get('error') or {}).get('code')} "
                                   f"{(resp.get('error') or {}).get('message', '')[:160]}")
            ef = fm(resp["result"])
            if ef["status"]["value"] != "emitted":
                raise RuntimeError(f"{what}: status={ef['status']['value']} "
                                   f"{ef['diagnostic']['value'][:200]}")
            return "".join(p["value"] for p in ef["sourceParts"]["value"])

        header = invoke("pep-c23-section",
                        [sliced["ascii_letter"], reports["ascii_letter"],
                         typed("Str", "header")], "header")
        units, emitted = "", []
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
        gate.row("epilogue:grant-wrapper", "pep_source_data" in epilogue,
                 "pep_source_data present" if "pep_source_data" in epilogue
                 else "NO grant wrapper")

        # ---- fact negatives, plus the false-positive control that makes them mean something
        def unit_emit(report):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-unit",
                                 "arguments": [sliced["main"], report, typed("Int", 0)],
                                 "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                error = resp.get("error") or {}
                return None, f"{error.get('code')} {error.get('message', '')}".strip()
            ef = fm(resp["result"])
            if ef["status"]["value"] != "emitted":
                return None, str(ef["diagnostic"]["value"])
            return "".join(p["value"] for p in ef["sourceParts"]["value"]), None

        honest, honest_why = unit_emit(reports["main"])
        gate.row("facts:honest-control", honest is not None,
                 f"emitted {len(honest)} bytes" if honest else f"FALSE REFUSAL {honest_why}")

        shapes = tampered_reports(reports, "main")
        if shapes is None:
            gate.row("facts:buildable", False, "main report carries no resolved calls")
        else:
            for (name, needle), tampered in zip(NEGATIVE_FACTS, shapes):
                piece, why = unit_emit(tampered)
                if piece is not None:
                    gate.row(name, False, "FAIL: expected refusal, got emission")
                elif needle not in why:
                    gate.row(name, False, f"FAIL: refusal {why!r} lacks {needle!r}")
                else:
                    gate.row(name, True, needle)

        other_target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                     "name": "a4-source-scan-stale",
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
                 else stale_text[:200])

        assembled = {"docorder": header + units + epilogue,
                     "protofirst": header + prototypes + units + epilogue}
        return assembled, by_name
    finally:
        session.close()


def oracle_seed(by_name, payload, out_path):
    """Layer 3. The app's own predicates, byte values via a typed List[Int] parameter."""
    src = "".join(by_name[n] + "\n"
                  for n in ("ascii_letter", "ascii_digit", "ascii_continue"))
    src += ("fn count_from(bytes: List[Int]) -> Int {\n"
            "  var n = 0\n"
            "  var first = true\n"
            "  var prev_continue = false\n"
            "  for b in bytes {\n"
            "    if ascii_letter(b) {\n"
            "      if first { n = n + 1 } else {\n"
            "        if prev_continue {\n"
            "        } else { n = n + 1 }\n"
            "      }\n"
            "    } else {\n"
            "    }\n"
            "    prev_continue = ascii_continue(b)\n"
            "    first = false\n"
            "  }\n"
            "  return n\n"
            "}\n")
    src += "say(int_text(count_from([" + ", ".join(str(b) for b in payload) + "])))\n"
    out_path.write_text(src, encoding="utf-8", newline="\n")
    ran = subprocess.run([str(SEED), "run", str(out_path)],
                         capture_output=True, text=True, check=False)
    if ran.returncode:
        return None, ran.stderr.strip()[:240]
    return ran.stdout.replace("\r\n", "\n").strip(), None


def main():
    as_json = "--json" in sys.argv
    gate = Gate()

    try:
        app_path, app_bytes_pinned = materialise(APP_REL)
    except RuntimeError as error:
        print(f"FAIL: cannot materialise the pinned application: {error}")
        return 1
    gate.row("app:pinned-bytes", True,
             f"materialised {len(app_bytes_pinned)} committed bytes; "
             f"sha256={hashlib.sha256(app_bytes_pinned).hexdigest()[:16]}")
    variant = os.environ.get("PEPIN_APP_VARIANT")
    if variant:
        app_path = pathlib.Path(variant)
        app_bytes_pinned = app_path.read_bytes()
        gate.row("app:DIAGNOSTIC-VARIANT", False,
                 f"NOT THE FROZEN APP: running A3 diagnostic variant {variant}. Every other "
                 f"row below describes the variant, not spec/agent4-spec-lab@12e143f")
        print("=" * 78)
        print("DIAGNOSTIC VARIANT RUN - this is NOT a gate of A4's frozen application")
        print("=" * 78)
    worktree_copy = ROOT / APP_REL
    if worktree_copy.is_file():
        wtb = worktree_copy.read_bytes()
        crlf = wtb.count(bytes((13, 10)))
        gate.row("provenance:worktree-vs-pinned", True,
                 f"checked-out copy {len(wtb)} B (crlf_pairs={crlf}) vs pinned "
                 f"{len(app_bytes_pinned)} B -- every run below uses the pinned bytes")
    if not SEED.is_file():
        built = BUILD / "ocaml" / "pep.exe"
        if not built.is_file():
            print("FAIL: no seed binary; run .\\pep.ps1 run examples/hello.pep first")
            return 1
        SEED.parent.mkdir(parents=True, exist_ok=True)
        SEED.write_bytes(built.read_bytes())

    oracle_only = "--oracle-only" in sys.argv
    if oracle_only:
        pfc = load("pfc", ROOT / "tests" / "probe_function_closure.py")
        _, app_functions = pfc.split_source(app_bytes_pinned.decode("utf-8"))
        assembled, by_name = {}, dict(app_functions)
        gate.row("mode:oracle-only", True,
                 "layers 2 and 3 only (independent oracle + seed interpreter); no emitter and "
                 "no native build, so this run certifies NO native result")
    else:
        try:
            assembled, by_name = emit_pipeline(gate, app_path)
        except RuntimeError as error:
            gate.row("emit:all", False, f"FIRST REFUSAL {error}")
            assembled, by_name = None, {}
    if assembled is None:
        _report(gate, as_json, None, oracle_only)
        return 1

    binaries = {}
    for order, c_source in assembled.items():
        c_path = BUILD / f"idruns_025_{order}.c"
        c_path.write_text(c_source, encoding="utf-8", newline="\n")
        for name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
            exe = BUILD / f"idruns_025_{order}_{name}.exe"
            built = subprocess.run(
                [str(pep_c23.compiler_path(name)), *extra,
                 "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                 str(c_path), "-o", str(exe)],
                capture_output=True, text=True, check=False)
            gate.row(f"build:{order}:{name}", built.returncode == 0,
                     built.stderr.strip()[:300] or "clean")
            if built.returncode == 0:
                binaries[f"{order}:{name}"] = exe

    # ---- pre-registered unseen corpus: layers 2, 3, 4 -----------------------
    for file_name in ORDER:
        path = CORPUS / file_name
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        hand = PREDICTED[file_name]
        ref = oracle_count(path)
        gate.row(f"bytes:{file_name}", digest == EXPECTED_SHA256[file_name],
                 f"sha256={digest[:16]} expected={EXPECTED_SHA256[file_name][:16]} "
                 f"bytes={len(payload)}")
        gate.row(f"oracle:{file_name}", ref == hand,
                 f"hand={hand} python_oracle={ref} sha256={digest[:16]} bytes={len(payload)}")
        seed_value, seed_error = oracle_seed(
            by_name, payload, BUILD / f"idruns_025_seed_{file_name}.pep")
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

    # ---- A4's own fixtures: checking A4's reference (layer 1 vs 2) ----------
    for rel, claimed in A4_CLAIMS.items():
        try:
            path, _pinned = materialise(rel)
        except RuntimeError as error:
            gate.row(f"a4:{rel}", False, f"cannot materialise pinned bytes: {error}")
            continue
        ref = oracle_count(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        gate.row(f"a4-reference:{rel}", ref == claimed,
                 f"a4_claims={claimed} a3_oracle={ref} sha256={digest[:16]} "
                 f"bytes={len(path.read_bytes())}")
        for key, exe in binaries.items():
            ran = subprocess.run([str(exe), str(path)], capture_output=True, text=True,
                                 check=False)
            got = ran.stdout.replace("\r\n", "\n").strip()
            gate.row(f"a4-native:{key}:{rel}",
                     ran.returncode == 0 and got == str(ref),
                     f"stdout={got!r} exit={ran.returncode} "
                     f"stderr={ran.stderr.strip()[:80]!r} oracle={ref}")

    # ---- metamorphic: one binary, six unseen files --------------------------
    if binaries:
        exe = binaries["docorder:clang"]
        seen = [subprocess.run([str(exe), str(CORPUS / f)], capture_output=True,
                               text=True, check=False).stdout.replace("\r\n", "\n").strip()
                for f in ORDER]
        gate.row("metamorphic:one-binary-six-files",
                 seen == [str(PREDICTED[f]) for f in ORDER],
                 f"answers={seen} (a constant printer fails here)")

        # ---- path negatives -------------------------------------------------
        missing = subprocess.run([str(exe), str(BUILD / "absent-025.pep")],
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

    _report(gate, as_json, {"predicted": PREDICTED,
                            "assembled_bytes": {k: len(v) for k, v in assembled.items()}},
            oracle_only)
    return 0 if all(r["ok"] for r in gate.rows) else 1


def _report(gate, as_json, extra, oracle_only=False):
    ok = all(r["ok"] for r in gate.rows)
    # A run without an emitted binary must never be labelled PROVEN: layers 2-3 agreeing is
    # not a native result, and this workshop has already been burned by inflated labels.
    verdict = ("PROVEN-ORACLE-ONLY" if oracle_only else "PROVEN") if ok else "FAIL"
    if as_json:
        print(json.dumps({"verdict": verdict, "oracle_only": oracle_only,
                          "checks": gate.rows, "extra": extra}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<46} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("identifier-start-run gate:", verdict if ok else f"FAIL {failed}",
              "(NO native evidence: oracle/seed layers only)" if oracle_only and ok else "")


if __name__ == "__main__":
    sys.exit(main())
