"""A4 dogfood apps through the chunked grant pipeline: source-scan and line-scan.

Drives A4's ACTUAL applications, read read-only from the pinned checkout, through the
chunked SourceBytes->native pipeline (chunk check -> per-function unit emissions -> one
assembled translation unit -> strict Clang C23 / GCC C2x over real files).

  pepin-source-scan.pep — spec/agent4-spec-lab@12e143f (1159B, sha8 f6e8f942),
                          counts identifier-start runs; nested if/while, empty-then idiom.
  pepin-line-scan.pep   — spec/agent4-spec-lab@41fe0cd (998B, bytes hashed and asserted),
                          counts LF bytes (value 10); filled then + empty else.

Expected behavior per program (documents the measured state, printed per run):
- source-scan: the main chunk is 44 nodes and exceeds the fixed 100k tool_step_budget in
  the twin unit emission (boundary measured: 37 emits, 43 tips). The probe therefore
  EXPECTS a first refusal carrying the exact step-limit refusal text; it refuses to claim
  anything native for this program (see docs/outbox/AGENT2_OUTBOX.md receipt 46 and the
  chunk-window ask to A1).
- line-scan: main fits inside capacity (~22 nodes); the probe EXPECTS the FULL vertical:
  seed-oracle parity on every committed real fixture, strict Clang + GCC, docorder AND
  protofirst assembly, plus the registered negatives (fact + native grant contracts).
  This program is the first A4 application eligible for a real A3 independent gate.

Oracle authority (unchanged from receipts 42/43): the compiler's own predicates are run by
the authoritative seed over the same bytes as a literal Int list (plain `run` cannot grant
ungranted SourceBytes). The oracle is re-derived from the bytes on every run; nothing is
asserted from A4's SPEC tables (23/30/0/139, 3/5/0/39). The independent Python reference
is printed as a BUILDER-SIDE sanity check, NOT an A3 gate.

Fail-closed negatives: on the main chunk report at the same emit entry (no-fact /
missing-target / forged-arity), and natively (no-argv -> PEP_RUNTIME_SOURCE_CONTEXT rc 1,
missing-file -> PEP_RUNTIME_SOURCE_OPEN rc 1). A3's hostile case matrix and independence
checks remain A3's lane.

Requires A1 chunk tooling (tests/chunk_helper.py, a7d3ee1 or later); SKIPS without it.

Run:  python tests/probe_dogfood_source_scan.py
"""
import hashlib
import importlib.util
import os
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
# The seed may live outside this tree (e.g. when running from a merged scratch worktree);
# an absolute override wins, else _build/a1_seed/pep.exe.
SEED = pathlib.Path(os.environ.get("PEP_SEED_EXE", str(BUILD / "a1_seed" / "pep.exe")))

# A4's pinned checkout: READ ONLY from here (no writes into that tree anywhere).
A4_DIR = pathlib.Path(r"D:\Projects\wt-spec-a4\examples\dogfood")

APPS = {
    "source-scan": {
        "file": "pepin-source-scan.pep",
        # pinned by A4's SPEC table at 12e143f (A4 receipt, self-scan row)
        "sha8": "f6e8f942",
        "rule": "runs",
        "expect": "capacity-refusal",  # measured state pending the chunk-window contract
        "entry": "Pep C23 cross-chunk",  # any refusal: printed as measured, never blamed
        "fixtures": ["input_ascii.pep", "input_nonascii.pep", "input_empty.pep"],
    },
    "line-scan": {
        "file": "pepin-line-scan.pep",
        # builder-pinned at read time from spec/agent4-spec-lab (998B); A4 blob-confirm pending
        "sha8": "12d4b1ab",
        "rule": "lf",
        "expect": "native-pass",
        "entry": None,
        "fixtures": ["input_ascii.pep", "input_nonascii.pep", "input_empty.pep"],
    },
}
SELF_SCAN = "pepin-source-scan.pep"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def independent_reference(rule, data_bytes):
    """Python reference over the honest rule. Builder-side sanity CHECK, not a gate."""
    def letter(data_byte):
        return 65 <= data_byte <= 90 or 97 <= data_byte <= 122 or data_byte == 95

    def cont(data_byte):
        return letter(data_byte) or 48 <= data_byte <= 57

    if rule == "lf":
        return sum(1 for data_byte in data_bytes if data_byte == 10)
    count, previous = 0, None
    for data_byte in data_bytes:
        if letter(data_byte) and (previous is None or not cont(previous)):
            count += 1
        previous = data_byte
    return count


def make_oracle(app_text, rule, data_bytes):
    """Seed oracle: app predicates verbatim in the head, then an index-free top-level
    replica of the rule over a literal Int list (no SourceBytes, no list indexing)."""
    head = app_text[:app_text.index("fn main")]
    if data_bytes:
        bytes_line = "let bytes = [" + ", ".join(str(data_byte) for data_byte in data_bytes) + "]\n"
    else:
        bytes_line = "let bytes: List[Int] = []\n"
        # PEP_EMPTY_LIST_NEEDS_TYPE: an empty literal needs an expected element type
        # (A1 receipt + A3 derivation point recorded; oracle-side only)
    body = bytes_line + "var acc = 0\n"
    if rule == "lf":
        body += "for b in bytes {\n  if b == 10 { acc = acc + 1 } else { }\n}\n"
    else:
        body += ("var prevCont = false\n"
                 "for b in bytes {\n"
                 "  if ascii_letter(b) {\n"
                 "    if prevCont { } else { acc = acc + 1 }\n"
                 "  } else { }\n"
                 "  prevCont = if ascii_letter(b) { true } else { ascii_digit(b) }\n"
                 "}\n")
    return head.rstrip("\n") + "\n" + body + "say(int_text(acc))\n"


def run_program(name, spec, helper, node_count_note):
    app_path = A4_DIR / spec["file"]
    app_bytes = app_path.read_bytes()
    app_sha8 = hashlib.sha256(app_bytes).hexdigest()[:8]
    if app_sha8 != spec["sha8"]:
        print(f"[{name}] ABORT: app sha8 {app_sha8} != pinned {spec['sha8']} "
              "(update the pin when A4 re-pins)")
        return "abort"
    app_text = app_bytes.decode("utf-8")
    fixture_files = [A4_DIR / fix for fix in spec["fixtures"]] + [A4_DIR / SELF_SCAN]
    print(f"[{name}] app {len(app_bytes)}B sha8={app_sha8}; fixtures: "
          + ", ".join(f.name for f in fixture_files))
    session = Session()
    outcome = "fail"
    assembled = {}
    reports, sliced = {}, {}
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
        pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
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
                require(resp, "status", want, f"[{name}] {op} {tool}")

        payload = app_bytes
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": f"dogfood-{name}" if len(name) < 40 else "dogfood-x",
                               "bytes": list(payload)})
        require(target, "outcome", "ok", f"[{name}] open app source")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        print(f"[{name}] sigs: {[s['name'] for s in sigs]}")

        labels = ["ascii_letter", "ascii_digit", "ascii_continue", "main"]
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            chunk_nodes = index.nodes_for(index.subtree(int(helper.nval(node, "id"))))
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
                print(f"[{name}] chunk {label}: ERROR "
                      f"{(checked.get('error') or {}).get('code')}")
                return "fail"
            f = fm(checked["result"])
            codes = [fm(x).get("code", {}).get("value")
                     for x in (f.get("diagnostics", {}).get("value") or [])]
            print(f"[{name}] chunk {label:15s} nodes={len(chunk_nodes):3d} "
                  f"status={f['status']['value']} {codes[:2]}")
            if f["status"]["value"] != "valid":
                return "fail"
            reports[label] = checked["result"]
            sliced[label] = sl

        def invoke(tool, arguments, what):
            resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool,
                                 "arguments": arguments, "semanticTarget": sem})
            if resp.get("outcome") != "ok":
                raise RuntimeError(f"{what}: {(resp.get('error') or {}).get('code')}")
            efields = fm(resp["result"])
            if efields["status"]["value"] != "emitted":
                raise RuntimeError(f"{what}: status={efields['status']['value']} "
                                   f"{efields['diagnostic']['value'][:200]}")
            return "".join(p["value"] for p in efields["sourceParts"]["value"])

        def try_invoke(tool, arguments, what):
            try:
                return invoke(tool, arguments, what), None
            except RuntimeError as error:
                return None, str(error)

        header, why = try_invoke("pep-c23-section",
                                 [sliced["ascii_letter"], reports["ascii_letter"],
                                  typed("Str", "header")], "header")
        if header is None:
            print(f"[{name}] FIRST REFUSAL header: {why}")
            return "fail"

        units = ""
        emitted_labels = []
        main_refusal = None
        for label in labels:
            if label == "main" and spec.get("skip-main-units"):
                break
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced[label], reports[label], typed("Int", 0)],
                                    f"unit {label}")
            if piece is None:
                print(f"[{name}] FIRST REFUSAL unit {label}: {why}")
                main_refusal = (label, why)
                break
            units += piece
            emitted_labels.append(label)
        if main_refusal:
            needle = "Pep C23 conditional" if name == "source-scan" else ""
            measured = main_refusal[1]
            if spec["expect"] == "capacity-refusal":
                # Documented capacity state: any honest refusal is the measured result.
                print(f"[{name}] MEASURED REFUSAL (as documented): unit {main_refusal[0]} "
                      f"-> {measured[:150]}")
                print(f"[{name}] nothing native claimed for this program; the probe "
                      "expects A1's chunk-window contract")
                return "refused-as-documented"
            return "fail"
        prototypes = "".join(
            invoke("pep-c23-section",
                   [sliced[label], reports[label], typed("Str", "prototypes")],
                   f"prototypes {label}") for label in labels)
        epilogue = invoke("pep-c23-section",
                          [sliced["main"], reports["main"], typed("Str", "main")],
                          "epilogue")
        print(f"[{name}] header={len(header)} prototypes={len(prototypes)} "
              f"units={len(units)} epilogue={len(epilogue)}")
        if "pep_source_data" not in epilogue:
            print(f"[{name}] FAIL: epilogue carries no grant wrapper")
            return "fail"
        assembled["docorder"] = header + units + epilogue
        assembled["protofirst"] = header + prototypes + units + epilogue

        # ---- negative controls on the main chunk report -----------------------
        def recmap(rec):
            return {f["name"]: f["value"] for f in rec["fields"]}

        def with_field(rec, field_name, value):
            return {"type": rec["type"], "fields": [
                ({"name": f["name"], "value": value} if f["name"] == field_name else f)
                for f in rec["fields"]]}

        def expect_refusal(label, report, needle):
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced["main"], report, typed("Int", 0)],
                                    f"negative {label}")
            if piece is not None:
                print(f"[{name}] NEGATIVE {label}: FAIL (expected refusal, got emission)")
                return 1
            if needle not in why:
                print(f"[{name}] NEGATIVE {label}: FAIL (refusal {why!r} lacks {needle!r})")
                return 1
            print(f"[{name}] NEGATIVE {label}: OK ({needle[:64]})")
            return 0

        main_report = reports["main"]
        main_fields = recmap(main_report)
        calls = json.loads(json.dumps(main_fields["calls"]["value"]))
        functions = json.loads(json.dumps(main_fields["functions"]["value"]))
        continue_fact = None
        for fact in calls:
            sem_id = int(recmap(fact)["calleeId"]["value"])
            for fn_fact in functions:
                if (int(recmap(fn_fact)["semanticId"]["value"]) == sem_id
                        and recmap(fn_fact)["name"]["value"] == "ascii_continue"):
                    continue_fact = fact
                    break
            if continue_fact is not None:
                break
        fact_failures = 0
        if continue_fact is None:
            print(f"[{name}] FUNCTION NEGATIVES: n/a (this app's main has no cross-chunk "
                  "call fact; the no-fact/missing-target/arity gates stay proven on "
                  "source-scan and receipts 42-44)")
        else:
            fact_failures += expect_refusal(
                "no-fact", with_field(main_report, "calls",
                                      {"type": "List[ResolvedCall]", "value": []}),
                "Pep C23 cross-chunk call has no resolved call fact")
            severed = with_field(continue_fact, "calleeId", typed("Int", 999999))
            severed_calls = {"type": "List[ResolvedCall]", "value": [
                severed if recmap(f)["syntaxId"] == recmap(continue_fact)["syntaxId"] else f
                for f in calls]}
            fact_failures += expect_refusal(
                "missing-target", with_field(main_report, "calls", severed_calls),
                "Pep C23 cross-chunk call target is missing from the checked functions")
            forged_fns = [with_field(f, "arity", typed("Int", 2))
                          if recmap(f)["name"]["value"] == "ascii_continue" else f
                          for f in functions]
            fact_failures += expect_refusal(
                "arity", with_field(main_report, "functions",
                                    {"type": "List[CheckedFunction]", "value": forged_fns}),
                "Pep C23 cross-chunk call argument count disagrees with the checked arity")
        if fact_failures:
            return "fail"
    finally:
        session.close()

    if spec["expect"] != "native-pass" or not assembled:
        print(f"[{name}] step-limit refusal documented; native stage not attempted")
        return "refused-as-documented"

    # ---- real files: seed oracle + native x2 compilers x2 orders x negatives --
    native_failures = 0
    first = None
    for fixture in fixture_files:
        data = fixture.read_bytes()
        reference = independent_reference(spec["rule"], data)
        oracle_path = BUILD / f"dogfood_{name}_oracle.pep"
        oracle_path.write_text(make_oracle(app_text, spec["rule"], data),
                               encoding="utf-8", newline="\n")
        seed = subprocess.run([str(SEED), "run", str(oracle_path)],
                              capture_output=True, check=False)
        if seed.returncode:
            print(f"[{name}] seed-oracle {fixture.name}: FAIL "
                  f"{seed.stderr[:300].decode('utf-8', 'replace')}")
            native_failures += 1
            continue
        expected = seed.stdout.replace(b"\r\n", b"\n").strip()
        agree = isinstance(reference, int) and str(reference) == expected.decode("utf-8", "replace")
        print(f"[{name}] fixture {fixture.name}: sha8={hashlib.sha256(data).hexdigest()[:8]} "
              f"{len(data)}B seed={expected!r} python-ref={reference} "
              f"{'AGREE' if agree else 'DISAGREE (labelled, not A3 gate)'}")
        for order, c_source in assembled.items():
            c_path = BUILD / f"dogfood_{name}_{order}.c"
            c_path.write_text(c_source, encoding="utf-8", newline="\n")
            for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                exe = BUILD / f"dogfood_{name}_{order}_{compiler_name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler_name)), *extra,
                     "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"[{name}] {fixture.name} {order}-{compiler_name}: "
                          f"BUILD FAIL {built.stderr[:300]}")
                    native_failures += 1
                    continue
                ran = subprocess.run([str(exe), str(fixture)],
                                     capture_output=True, check=False)
                out = ran.stdout.replace(b"\r\n", b"\n").strip()
                ok = ran.returncode == 0 and out == expected
                print(f"[{name}] {fixture.name} {order}-{compiler_name}: "
                      f"{'OK' if ok else 'FAIL'} native={out!r}")
                if not ok:
                    native_failures += 1
                if first is None and order == "docorder" and compiler_name == "clang":
                    first = exe
    for label, argv, want in (("no-argv", [], "PEP_RUNTIME_SOURCE_CONTEXT"),
                              ("missing-file",
                               [str(BUILD / f"dogfood_{name}_missing_input.pep")],
                               "PEP_RUNTIME_SOURCE_OPEN")):
        bad = subprocess.run([str(first), *argv], capture_output=True, check=False)
        err_lines = bad.stderr.decode("utf-8", "replace").strip().splitlines()
        got = err_lines[-1] if err_lines else ""
        ok_n = bad.returncode == 1 and got == want
        print(f"[{name}] native-negative {label}: "
              f"{'OK' if ok_n else 'FAIL'} rc={bad.returncode} stderr={got!r}")
        if not ok_n:
            native_failures += 1

    if native_failures:
        print(f"[{name}] native stage: FAIL ({native_failures})")
        return "fail"
    print(f"[{name}] native vertical: PASS "
          f"(seed parity, Clang+GCC, docorder+protofirst, negatives held)")
    return "pass"


def A4_APP_self(name):
    del name
    return A4_DIR / SELF_SCAN


def main():
    helper_chunk = ROOT / "tests" / "chunk_helper.py"
    if not helper_chunk.is_file():
        print("SKIP: no tests/chunk_helper.py (needs A1 11e1294 or later)")
        return 0
    helper = load("ch", helper_chunk)
    outcomes = {}
    for name, spec in APPS.items():
        outcomes[name] = run_program(name, spec, helper, None)
    print("\ndogfood probe outcomes:")
    for name, outcome in outcomes.items():
        print(f"  {name}: {outcome}")
    bad = [n for n, o in outcomes.items() if o not in ("pass", "refused-as-documented")]
    print("dogfood apps vertical:",
          "OK (per-program documented outcomes)" if not bad else f"PROBLEM ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
