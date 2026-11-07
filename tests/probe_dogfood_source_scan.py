"""A4 dogfood app through the chunked grant pipeline: pepin-source-scan.

Program under test is A4's ACTUAL application at spec/agent4-spec-lab@12e143f
(examples/dogfood/pepin-source-scan.pep, 1159 bytes, sha8 asserted below
against SPEC f6e8f942):

  fn ascii_letter / ascii_digit / ascii_continue   verbatim lexer predicates
  fn main(source: SourceBytes) -> Int              identifier-start runs over (n, o)

New shapes vs the receipts-42/43 scan main, each a candidate first refusing layer:
- while condition `!(byte_length(source) <= o)` -- cross-chunk call inside a UNARY NOT
- `if ascii_letter(byte_at(source, o))` inside the while body (call in If condition,
  twin-threaded since 689c38a), then `if o == 0` nested inside that branch
- a NESTED if inside an if BODY, another inside an ELSE branch, and an EMPTY then arm
  on the nested `if ascii_continue(...)` (empty branch lowering)
- `byte_at(source, o - 1)` -- binary arithmetic inside a cross-chunk call argument

Owner lanes: this probe + any subsequent emitter/runtime fix = A2 (this branch). A4's
app source and fixtures are READ-ONLY here, read from the pinned checkout; the probe
hashes every byte it consumes and asserts the SPEC sha8.

Native stage (strict Clang C23 + GCC C2x -Wall -Wextra -Wpedantic -Werror -O2):
for each of FOUR committed real files (A4's three fixtures + self-scan; size+sha8
printed), the assembled binary must exit 0 and print one integer line equal to:
(a) the seed oracle -- the app's OWN predicates executed by the authoritative seed
    over the same bytes, given as a literal Int list (the receipts-42/43 authority
    boundary: plain `run` cannot grant ungranted SourceBytes), and
(b) an independent Python reference over the honest rule (builder-side sanity check;
    NOT an A3 independent gate and labelled as such).
The 23/30/0/139 values in A4's SPEC table are never asserted directly; the expected
number is re-derived from the bytes on every run.

Fail-closed negatives already registered (receipts 42-44) run on the main chunk
report at the same emit entry: no-fact / missing-target / forged-arity.
Native grant negatives (registered contract, emitter grant wrapper):
- no argv       -> PEP_RUNTIME_SOURCE_CONTEXT on stderr, exit 1
- missing file  -> PEP_RUNTIME_SOURCE_OPEN on stderr, exit 1

Requires A1 chunk tooling (tests/chunk_helper.py, a7d3ee1); SKIPS on a tree without it.

Run:  python tests/probe_dogfood_source_scan.py
"""
import hashlib
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
SEED = BUILD / "a1_seed" / "pep.exe"

# A4's pinned checkout: READ ONLY from here (no writes into that tree anywhere).
A4_APP = pathlib.Path(r"D:\Projects\wt-spec-a4\examples\dogfood\pepin-source-scan.pep")
A4_DIR = A4_APP.parent
EXPECTED_APP_SHA8 = "f6e8f942"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def independent_reference(data_bytes):
    """Python reference over the honest rule. Builder-side sanity CHECK, not a gate."""
    def letter(data_byte):
        return 65 <= data_byte <= 90 or 97 <= data_byte <= 122 or data_byte == 95

    def cont(data_byte):
        return letter(data_byte) or 48 <= data_byte <= 57

    count, previous = 0, None
    for data_byte in data_bytes:
        if letter(data_byte) and (previous is None or not cont(previous)):
            count += 1
        previous = data_byte
    return count


def make_oracle(app_text, data_bytes):
    """Seed oracle: app predicates `ascii_letter/ascii_digit/ascii_continue` FOR
    bytes[index] verbatim in the head, then an index-free top-level replica of the
    (n, o) run rule over a literal Int list (no SourceBytes, no list indexing)."""
    head = app_text[:app_text.index("fn main")]
    literals = ", ".join(str(data_byte) for data_byte in data_bytes)
    return (head.rstrip("\n") + "\n"
            + f"let bytes = [{literals}]\n"
            + "var acc = 0\nvar prevCont = false\n"
            + "for b in bytes {\n"
            + "  if ascii_letter(b) {\n"
            + "    if prevCont { } else { acc = acc + 1 }\n"
            + "  } else { }\n"
            + "  prevCont = if ascii_letter(b) { true } else { ascii_digit(b) }\n"
            + "}\n"
            + "say(int_text(acc))\n")


def main():
    app_bytes = A4_APP.read_bytes()
    app_sha8 = hashlib.sha256(app_bytes).hexdigest()[:8]
    if app_sha8 != EXPECTED_APP_SHA8:
        print(f"ABORT: app sha8 {app_sha8} != pinned {EXPECTED_APP_SHA8} "
              "(update EXPECTED_APP_SHA8 when A4 re-pins)")
        return 2
    app_text = A4_APP.read_text(encoding="utf-8")
    fixture_files = [A4_DIR / "input_ascii.pep", A4_DIR / "input_nonascii.pep",
                     A4_DIR / "input_empty.pep", A4_APP]
    print(f"app: A4 worktree {len(app_bytes)}B sha8={app_sha8}; fixtures: "
          + ", ".join(f"{f.name}" for f in fixture_files)
          + " (4th = self-scan)")

    chunk_helper_path = ROOT / "tests" / "chunk_helper.py"
    if not chunk_helper_path.is_file():
        print("SKIP: no tests/chunk_helper.py (needs A1 11e1294 or later)")
        return 0
    helper = load("ch", chunk_helper_path)

    failures = 0
    session = Session()
    assembled = {}
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
                require(resp, "status", want, f"{op} {tool}")

        payload = app_bytes
        target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "dogfood-source-scan", "bytes": list(payload)})
        require(target, "outcome", "ok", "open app source")
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": ["main"]}
        parsed = parse_target(session, payload, target, revision)
        pfields = fm(parsed)
        nodes = pfields["nodes"]["value"]
        index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
        print(f"sigs: {[s['name'] for s in sigs]}")

        labels = ["ascii_letter", "ascii_digit", "ascii_continue", "main"]
        reports, sliced = {}, {}
        for label in labels:
            node = next(n for n in nodes if helper.nval(n, "kind") == "function"
                        and helper.nval(n, "text") == label)
            subtree = index.subtree(int(helper.nval(node, "id")))
            keep = set(subtree)
            chunk_nodes = index.nodes_for(sorted(keep))
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
            print("\ndogfood vertical: INCOMPLETE at check stage")
            return 1

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
            print(f"FIRST REFUSAL header: {why}")
            return 1

        units = ""
        emitted_labels = []
        refusal = None
        for label in labels:
            piece, why = try_invoke("pep-c23-unit",
                                    [sliced[label], reports[label], typed("Int", 0)],
                                    f"unit {label}")
            if piece is None:
                print(f"FIRST REFUSAL unit {label}: {why}")
                refusal = (label, why)
                failures += 1
                break
            units += piece
            emitted_labels.append(label)
        if refusal:
            print(f"emitted units before the refusal: {emitted_labels}")
            return 1

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
        assembled["docorder"] = header + units + epilogue
        assembled["protofirst"] = header + prototypes + units + epilogue

        # ---- negative controls on the main chunk report -----------------------
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
        continue_sem = int(recmap(next(x for x in functions
                                       if recmap(x)["name"]["value"] == "ascii_continue"))
                           ["semanticId"]["value"])
        continue_fact = next(f for f in calls
                             if int(recmap(f)["calleeId"]["value"]) == continue_sem)
        failures += expect_refusal(
            "no-fact", with_field(main_report, "calls",
                                  {"type": "List[ResolvedCall]", "value": []}),
            "Pep C23 cross-chunk call has no resolved call fact")
        severed = with_field(continue_fact, "calleeId", typed("Int", 999999))
        severed_calls = {"type": "List[ResolvedCall]", "value": [
            severed if recmap(f)["syntaxId"] == recmap(continue_fact)["syntaxId"] else f
            for f in calls]}
        failures += expect_refusal(
            "missing-target", with_field(main_report, "calls", severed_calls),
            "Pep C23 cross-chunk call target is missing from the checked functions")
        forged_fns = [with_field(f, "arity", typed("Int", 2))
                      if recmap(f)["name"]["value"] == "ascii_continue" else f
                      for f in functions]
        failures += expect_refusal(
            "arity", with_field(main_report, "functions",
                                {"type": "List[CheckedFunction]", "value": forged_fns}),
            "Pep C23 cross-chunk call argument count disagrees with the checked arity")
    finally:
        session.close()

    if failures or not assembled:
        print(f"\ndogfood source-scan vertical: INCOMPLETE ({failures})")
        return 1

    # ---- real files: independent reference -> seed oracle -> native x2 x2 ----
    for fixture in fixture_files:
        data = fixture.read_bytes()
        record = (hashlib.sha256(data).hexdigest()[:8], len(data))
        reference = independent_reference(data)
        oracle_path = BUILD / "dogfood_source_scan_oracle.pep"
        oracle_path.write_text(make_oracle(app_text, data), encoding="utf-8", newline="\n")
        seed = subprocess.run([str(SEED), "run", str(oracle_path)],
                              capture_output=True, check=False)
        if seed.returncode:
            print(f"seed-oracle {fixture.name}: FAIL "
                  f"{seed.stderr[:300].decode('utf-8', 'replace')}")
            failures += 1
            continue
        expected = seed.stdout.replace(b"\r\n", b"\n").strip()
        agree = str(reference) == expected.decode("utf-8", "replace")
        print(f"fixture {fixture.name}: {record[0]} {record[1]}B "
              f"seed={expected!r} python-ref={reference} "
              f"{'AGREE' if agree else 'DISAGREE (labelled, not A3 gate)'}")
        for order, c_source in assembled.items():
            c_path = BUILD / f"dogfood_source_scan_{order}.c"
            c_path.write_text(c_source, encoding="utf-8", newline="\n")
            for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                exe = BUILD / f"dogfood_source_scan_{order}_{compiler_name}.exe"
                built = subprocess.run(
                    [str(pep_c23.compiler_path(compiler_name)), *extra,
                     "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                     str(c_path), "-o", str(exe)],
                    capture_output=True, text=True, check=False)
                if built.returncode:
                    print(f"{fixture.name} {order}-{compiler_name}: "
                          f"BUILD FAIL {built.stderr[:300]}")
                    failures += 1
                    continue
                ran = subprocess.run([str(exe), str(fixture)],
                                     capture_output=True, check=False)
                out = ran.stdout.replace(b"\r\n", b"\n").strip()
                ok = ran.returncode == 0 and out == expected
                print(f"{fixture.name} {order}-{compiler_name}: "
                      f"{'OK' if ok else 'FAIL'} native={out!r}")
                if not ok:
                    failures += 1
                if fixture is fixture_files[0] and order == "docorder" and compiler_name == "clang":
                    # registered grant negatives, one compiler, once
                    for label, argv, needle in (
                            ("no-argv", [], None),
                            ("missing-file", [str(BUILD / "dogfood_missing_input.pep")],
                             None)):
                        bad = subprocess.run([str(exe), *argv],
                                             capture_output=True, check=False)
                        err = bad.stderr.decode("utf-8", "replace").strip()
                        got = err.splitlines()[-1] if err else ""
                        want = ("PEP_RUNTIME_SOURCE_CONTEXT" if label == "no-argv"
                                else "PEP_RUNTIME_SOURCE_OPEN")
                        ok_n = bad.returncode == 1 and got == want
                        print(f"native-negative {label}: "
                              f"{'OK' if ok_n else 'FAIL'} "
                              f"rc={bad.returncode} stderr={got!r}")
                        if not ok_n:
                            failures += 1

    print("\ndogfood source-scan vertical:",
          "PASS" if not failures else f"FAIL ({failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
