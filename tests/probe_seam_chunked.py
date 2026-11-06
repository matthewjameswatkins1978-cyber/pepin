"""Seam demonstration: A1's checked-chunk contract driving MY bounded emitter (reproducible).

Auto-prepares pinned inputs, then mirrors A1's tests/test_lexer_chunk_ledger.py flow:
  git-fetch A1 codex/p1-checker-cost-fix at the pinned SHA, dump their lexer/parser/checker and
  compile their seed into _build/a1_seed (their checker needs the str_concat builtin) ->
  parse fixture -> per-chunk plan (decl closure + function subtree + referenced decls) ->
  analyze_chunk with external signatures -> MY header/units/epilogue emitted FROM CHUNK REPORTS.

Measured outputs recorded 2026-11-05 at A1 @2f939a0: all FOUR separately checked chunks are
status=valid (decl 18, make_token 55 -- matching A1's pinned ledger -- add_one 8, main 5);
header + the make_token, add_one and main units + epilogue all emit from those chunk reports;
the cross-chunk call `return add_one(41)` lowers through checked facts ONLY
(ResolvedCall.syntaxId -> exactly one CheckedFunction -> name-based pep_fn_<name> symbol, arity
re-checked, Int/Bool/locally-declared-record results only, stale/foreign facts refused at the
document/revision gate). Strict Clang AND GCC build the assembled C23 with
-Wall -Wextra -Wpedantic -Werror and run 42, matching the seed oracle exactly (entry-point
difference stated: the seed runs top-level statements, native runs fn main). The transport
helper numbers external signature ids per CALL, so this probe renumbers them uniquely after
fetch -- without that, two externals collide and the checker reports PEP_TYPE_MISMATCH (measured).
Budgets unchanged: a merged single-chunk plan still hits PEP_RUNTIME_STEP_LIMIT, so chunking
remains mandatory.
"""
import subprocess

A1_SHA = "727f8af4d019e6e5e235ac26077a12b166b9c080"
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "_build"


def prepare():
    subprocess.run(["git", "fetch", "origin", "codex/p1-checker-cost-fix"],
                   cwd=ROOT, check=True, capture_output=True)
    for source, output in (("examples/pep_lexer.pep", "a1_lexer.pep"),
                           ("examples/pep_parser.pep", "a1_parser.pep"),
                           ("tests/pep_checker_a13.pep", "a1_checker.pep"),
                           # Transport helper is fetched WITH the pin so the probe never runs a
                           # stale copy of A1's checked-fact marshaller against a newer checker.
                           ("tests/chunk_helper.py", "a1_chunk_helper.py"),
                           # The checked-chunk contract is A1's, not A2's: fetch it WITH the
                           # pin so a cold checkout imports the pinned contract instead of a
                           # stale _build copy (measured: a fresh worktree has no
                           # pep_chunk_contract.py at all, and the 4 Nov _build copy predates
                           # the 2ad750b pin marker).
                           ("pep_chunk_contract.py", "pep_chunk_contract.py"),
                           ("pep_ocaml.ml", "a1_seed/pep_ocaml.ml")):
        data = subprocess.run(["git", "show", f"{A1_SHA}:{source}"], cwd=ROOT, check=True,
                              capture_output=True).stdout
        target = BUILD / output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    exe = BUILD / "a1_seed" / "pep.exe"
    pin_marker = BUILD / "a1_seed" / "seed_source_pin.txt"
    # Fresh-checkout honesty (G-A2-6): the seed exe is a BUILD ARTIFACT of the pinned
    # pep_ocaml.ml, so rebuild whenever A1_SHA changes instead of silently trusting a cached
    # exe from an earlier pin (provenance of a bare pre-existing exe is unknowable). A fresh
    # checkout has no exe and takes the same path; a marker-less legacy exe rebuilds once.
    pin_matches = pin_marker.exists() and pin_marker.read_text(encoding="utf-8").strip() == A1_SHA
    if not exe.exists() or not pin_matches:
        exe.unlink(missing_ok=True)
        opam_root = os.environ.get("PEPIN_OPAM_ROOT") or str(pathlib.Path.home() / "AppData/Local/opam")
        subprocess.run(["opam", "exec", "--root", opam_root, "--switch", "pepin-5.5.2", "--",
                        "ocamlopt", "-o", str(exe), str(BUILD / "a1_seed" / "pep_ocaml.ml")],
                       cwd=ROOT, check=True)
    pin_marker.write_text(A1_SHA, encoding="utf-8")


prepare()
"""Seam demonstration: A1's checked-chunk contract driving MY bounded emitter.

Flow mirrors A1's tests/test_lexer_chunk_ledger.py exactly, at the A1_SHA pin below (2ad750b:
A1's G-A1-1 refusal of repeated/aliased external callee facts in one batch, on top of the
d64518f batch-unique signature-id fix that answered this probe's finding; ancestry includes the
R-ID-1 gate, union facts, T-REC pins and the f4eb231 CHECKED_CHUNK_CONTRACT) seed + checker
with MY emitter in this worktree:

  parse whole fixture -> plan chunks (decl closure + per-function subtree + referenced decls)
  -> analyze_chunk per slice with external signatures -> emit MY header/units/epilogue FROM THE
  CHUNK REPORTS -> assemble -> strict Clang+GCC -> execute.

Assembly is the A2 bounded-emission contract shape: header(from the declaration chunk) +
function units(from each function chunk) + epilogue(from the main chunk). Every piece is a real
emission over contract-checked nodes; nothing is hand-written C.
"""

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(".").resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))
import pep_c23  # noqa: E402
from pep_c23 import require, parse_target, typed  # noqa: E402

BUILD = ROOT / "_build"
A1_SEED = BUILD / "a1_seed" / "pep.exe"
LEXER = ROOT / "examples" / "pep_lexer.pep"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
helper = load("a1_chunk_helper", BUILD / "a1_chunk_helper.py")


class A1Session:
    def __init__(self):
        self.request_bytes_total = 0
        self.response_bytes_total = 0
        self.last_request_bytes = 0
        self.last_response_bytes = 0
        self.last_response = None
        self.process = subprocess.Popen(
            [str(A1_SEED), "session", "--jsonl"],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        )

    def send(self, request):
        encoded = json.dumps(request, ensure_ascii=False, separators=(",", ":"))
        self.process.stdin.write(encoded + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            detail = self.process.stderr.read()
            raise RuntimeError("A1 session ended without a response" + (": " + detail.strip() if detail else ""))
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=30)


def fields_map(record):
    return {f["name"]: f["value"] for f in record.get("fields", [])}


def nval(node, key):
    return fields_map(node).get(key, {}).get("value")


def stage(label, ok, detail=""):
    print(f"{label:16s} {'OK' if ok else 'FAIL'} {detail}")
    return ok


a1_lexer = (BUILD / "a1_lexer.pep").read_text(encoding="utf-8")
a1_parser = (BUILD / "a1_parser.pep").read_text(encoding="utf-8")
a1_checker = (BUILD / "a1_checker.pep").read_text(encoding="utf-8")
my_emitter = (ROOT / "tests" / "pep_c23_emitter.pep").read_text(encoding="utf-8")

lines = LEXER.read_text(encoding="utf-8").split("\n")
lex_chunk = "\n".join(lines[2:12]) + "\n" + "\n".join(lines[112:122]) + "\n"
# Distinct chunks: declaration (LexToken), real lexer function (make_token), a scalar-result
# callee (add_one) whose cross-chunk call result IS the program's output, and main. The record
# field access on a cross-chunk record result is a measured boundary, kept out of the runnable
# fixture rather than hidden (see the receipt).
fixture = (lex_chunk +
           "fn add_one(v: Int) -> Int {\n"
           "  return v + 1\n"
           "}\n"
           "fn main() -> Int {\n"
           "  return add_one(41)\n"
           "}\n")

bundle = "\n".join([a1_lexer, a1_parser, a1_checker, my_emitter])
print("bundle_sha256", hashlib.sha256(bundle.encode()).hexdigest())

session = A1Session()
try:
    opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                           "name": "seam-bundle", "metadataOnly": True})
    if opened.get("outcome") != "ok" or opened.get("status") != "valid":
        stage("bundle-open", False, str((opened.get("diagnostics") or [])[:2])[:400])
        sys.exit(1)
    stage("bundle-open", True, "A1 seed accepts A1 lexer+parser+checker + my emitter")
    document, revision = opened["document"], opened["revision"]

    sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "validate", "bytes": []})
    pic.register(session, document, revision, sample["document"], sample["revision"])
    # A1's chunk tools on the same bundle.
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    empty_pp = pep_c23.parser_progress(sample["document"], sample["revision"])
    empty_ext = {"type": "List[CheckedFunction]", "value": []}
    empty_sig = {"type": "List[ResolvedSignature]", "value": []}
    for tool, function, arguments, expect in [
            # A1's own cross-chunk call test (test_chunk_cross_call_facts.py @2f939a0) checks the
            # caller chunk through analyze_chunk_typed with external types and expectReturns --
            # that is the entry whose external-signature argument typing is verified; the
            # untyped analyze_chunk draws PEP_TYPE_MISMATCH on the same valid source (measured).
            ("pep-c23-checker-chunk", "analyze_chunk_typed",
             [empty_pp, empty_ext, empty_sig,
              {"type": "List[ResolvedTypeDecl]", "value": []},
              {"type": "Bool", "value": True}],
             pep_c23.checker_report(sample["document"], sample["revision"])),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty_pp], empty_sig)]:
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                      "tool": tool, "document": document, "revision": revision, "function": function})
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool, "document": document,
                                  "revision": revision,
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}")
        session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                      "tool": tool, "document": document, "revision": revision})
    refused = pep_c23.typed_record("unsupported", (),
                                   "Pep C23 emission requires a top-level function named main")
    session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                  "tool": "pep-c23-section", "document": document, "revision": revision,
                  "function": "emit_c23_section"})
    validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                              "op": "tool_validate", "tool": "pep-c23-section",
                              "document": document, "revision": revision,
                              "testVectors": [{"arguments": [empty_pp,
                                                pep_c23.checker_report(sample["document"], sample["revision"]),
                                                typed("Str", "header")],
                                               "expect": refused, "semanticTarget": target_spec}]})
    require(validated, "status", "Validated", "validate pep-c23-section")
    session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                  "tool": "pep-c23-section", "document": document, "revision": revision})

    payload = fixture.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": "seam-fixture", "bytes": list(payload)})
    require(target, "outcome", "ok", "open fixture")
    sem = {"document": target["document"], "revision": target["revision"], "entryFunctions": []}
    parsed = parse_target(session, payload, target, revision)
    pfields = fields_map(parsed)
    stage("parse", pfields["status"]["value"] == "complete",
          f"nodes={len(pfields['nodes']['value'])} bytes={len(payload)}")

    sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
    # HISTORY (measured, kept for A3): the helper numbered ids per header chunk, so aggregated
    # externals collided at 9000/1000000000 -- at 2f939a0 the checker resolved add_one(41)
    # against make_token's Str parameter (PEP_TYPE_MISMATCH on the integer), A1's own pin test
    # failed at 4c4064e with [9000, 9000, 9000], and the cited repair 9e32999 did not exist
    # (all reproduced read-only 2026-11-04; A1 corrected the record in BOOT-A1-20261104-028).
    # RESOLUTION: A1's F1 fix at d64518f renumbers batch-unique ids INSIDE fetch_all_sigs (the
    # owner boundary), and per A1's -028 instruction this probe's local renumber workaround is
    # REMOVED: raw ids are the contract now. Detection remains and FAILS LOUDLY on a collision
    # -- a residual mismatch is an A1-side finding to report, never to paper over. A3 can
    # reproduce the historical raw failure at the pinned pre-fix probe revision (df190de).
    rawSemids = [signature["semid"] for signature in sigs]
    collisionDetected = len(set(rawSemids)) != len(sigs)
    stage("sig-id-state", not collisionDetected,
          f"raw_semids={rawSemids} collision={collisionDetected} renumber=removed(a1 d64518f owns uniqueness)")
    for s in sigs:
        print("SIG", s["name"], "arity", s["arity"], "rtype", s["rtype"], "id", s.get("id"), "semid", s["semid"], "synid", s["synid"])
    # Raw compiler-produced functionId for each function's header chunk (the helper discards it):
    for fn_node in [n for n in pfields["nodes"]["value"]
                    if helper.nval(n, "kind") == "function" and str(helper.nval(n, "parentId")) == "-1"]:
        sub = helper.header_subtree(pfields["nodes"]["value"],
                                    {str(helper.nval(n, "id")): n for n in pfields["nodes"]["value"]},
                                    helper.nval(fn_node, "id"))
        chunk = helper.remap_chunk([json.loads(json.dumps(n)) for n in sub])
        hp = {"type": "ParserProgress", "fields": [
            {"name": k, "value": ({"type": "List[FlatAstNode]", "value": chunk} if k == "nodes" else pfields[k])}
            for k in pfields]}
        r = session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                          "tool": "pep-c23-checker-sigs", "arguments": [hp], "semanticTarget": sem})
        raw = r["result"].get("value")
        if raw is None:
            raw = r["result"]["fields"][0]["value"]["value"]
        for entry in raw:
            fm = {f["name"]: f["value"] for f in entry["fields"]}
            print("RAW-SIG fn=%s functionId=%s" % (
                fm["functionName"]["value"], fm["functionId"]["value"]))
    nodes = pfields["nodes"]["value"]
    by_id = {str(helper.nval(node, "id")): node for node in nodes}
    index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
    functions = [n for n in nodes if helper.nval(n, "kind") == "function"
                 and str(helper.nval(n, "parentId")) == "-1"]
    decl_roots = [int(helper.nval(n, "id")) for n in nodes
                  if str(helper.nval(n, "parentId")) == "-1" and helper.nval(n, "kind") != "function"]
    decl_name_to_id = {helper.nval(n, "text"): str(helper.nval(n, "id")) for n in nodes
                       if str(helper.nval(n, "parentId")) == "-1"
                       and helper.nval(n, "kind") in ("record_declaration", "union_declaration")}
    v2u = helper.variant_to_union(nodes)
    sigs_by_name = {sig["name"]: sig for sig in sigs}

    # Chunk plan: one declaration chunk, then each function subtree plus the decl subtrees it
    # references -- the exact shape A1's ledger produces.
    chunk_ids, labels, kinds = [], [], []
    for root in decl_roots:
        chunk_ids.append(sorted(index.subtree(root)))
        labels.append(f"declaration:{helper.nval(by_id[str(root)], 'text')}")
        kinds.append("declaration")
    # Per-function chunks, exactly the shape A1's ledger pins (subtree + referenced declarations).
    for function in functions:
        subtree = index.subtree(int(helper.nval(function, "id")))
        sub_nodes = [json.loads(json.dumps(by_id[str(i)])) for i in subtree]
        extra = helper.decl_closure(nodes, sub_nodes, sigs_by_name, decl_name_to_id, v2u)
        extra_ids = {int(helper.nval(n, "id")) for n in extra} - set(subtree)
        chunk_ids.append(sorted(set(subtree) | extra_ids))
        labels.append(helper.nval(function, "text"))
        kinds.append("function")

    reports, sliced_by_label = {}, {}
    for position, label in enumerate(labels):
        planned = chunk_ids[position]
        chunk_nodes = index.nodes_for(planned)
        other = [sig for sig in sigs if int(sig["node"]) not in set(planned)]
        sliced = {"type": "ParserProgress", "fields": [
            {"name": key, "value": ({"type": "List[FlatAstNode]",
                                     "value": helper.remap_chunk(json.loads(json.dumps(chunk_nodes)))}
                                    if key == "nodes" else pfields[key])}
            for key in pfields]}
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sliced,
                                              {"type": "List[CheckedFunction]",
                                               "value": [helper.checked_fn_value(s) for s in other]},
                                              {"type": "List[ResolvedSignature]",
                                               "value": [helper.resolved_sig_value(s) for s in other]},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
        if checked.get("outcome") != "ok":
            stage(f"check:{label}", False, str(checked.get("error"))[:200])
            sys.exit(2)
        report = checked["result"]
        status = fields_map(report)["status"]["value"]
        diags = (fields_map(report)["diagnostics"]["value"] or [])[:2]
        remapped_now = next(f["value"]["value"] for f in sliced["fields"]
                            if f["name"] == "nodes")
        for d in diags:
            sid = int(fields_map(d).get("syntaxId", {}).get("value", -1))
            hit = [n for n in remapped_now if int(helper.nval(n, "id")) == sid]
            if hit:
                n0 = hit[0]
                print("    diag-node id=%s kind=%s text=%s" % (
                    sid, helper.nval(n0, "kind"), helper.nval(n0, "text")))
        stage(f"check:{label}", status == "valid",
              f"status={status} nodes={len(planned)} diags={json.dumps(diags)[:300]}")
        if status != "valid":
            sys.exit(3)
        reports[label] = report
        sliced_by_label[label] = sliced

    decl_label = labels[0]
    body_label = "make_token"
    callee_label = "add_one"
    main_label = "main"

    def invoke(tool, arguments, what):
        response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": tool, "arguments": arguments,
                                 "semanticTarget": sem})
        if response.get("outcome") != "ok":
            stage(what, False, str(response.get("error"))[:250])
            sys.exit(4)
        fields = {f["name"]: f["value"] for f in response["result"]["fields"]}
        status = fields["status"]["value"]
        parts = "".join(p["value"] for p in fields["sourceParts"]["value"]) \
            if fields["sourceParts"]["value"] else ""
        stage(what, status == "emitted",
              f"status={status}" + ("" if status == "emitted" else f" diag={fields['diagnostic']['value'][:200]}"))
        if status != "emitted":
            sys.exit(5)
        return parts

    header = invoke("pep-c23-section",
                    [sliced_by_label[decl_label], reports[decl_label], typed("Str", "header")],
                    "emit-header")
    unit_make = invoke("pep-c23-unit",
                       [sliced_by_label[body_label], reports[body_label], typed("Int", 0)],
                       "emit-unit-make_token")

    unit_add = invoke("pep-c23-unit",
                      [sliced_by_label[callee_label], reports[callee_label], typed("Int", 0)],
                      "emit-unit-add_one")
    unit_main = invoke("pep-c23-unit",
                       [sliced_by_label[main_label], reports[main_label], typed("Int", 0)],
                       "emit-unit-main")
    epilogue = invoke("pep-c23-section",
                      [sliced_by_label[main_label], reports[main_label], typed("Str", "main")],
                      "emit-epilogue")

    # Assembly order is document order over separately checked chunks: declaration header,
    # then each function unit (callees precede callers here), then the epilogue. The header
    # carries prototypes only for functions inside ITS chunk, so a caller emitted before its
    # callee would not compile -- unit order is part of the assembly contract (A2-3 negative).
    # G-A2-4: prototypes from each FUNCTION chunk's own checked nodes -- parameter types live
    # in the nodes, and the checked document/revision-gated report that authorises the unit
    # authorises these bytes too, so no new facts, tool argument or host-generated C involved.
    prototypes = ""
    for fn_label in (body_label, callee_label, main_label):
        prototypes += invoke("pep-c23-section",
                             [sliced_by_label[fn_label], reports[fn_label], typed("Str", "prototypes")],
                             f"emit-prototypes-{fn_label}")
    print(f"prototypes_bytes={len(prototypes)}")
    c_source = header + unit_make + unit_add + unit_main + epilogue
    c_path = BUILD / "seam_chunked.c"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    print(f"assembled_c_bytes={len(c_source)}")
    # Reverse-order assembly (caller unit FIRST, multiple callees present): only legal WITH
    # the prototypes block. The no-prototypes reverse order stays the pinned neg-unit-order
    # failure below, so both halves of the contract are live in one run.
    c_source_reverse = header + prototypes + unit_main + unit_add + unit_make + epilogue
    c_path_reverse = BUILD / "seam_chunked_reverse.c"
    c_path_reverse.write_text(c_source_reverse, encoding="utf-8", newline="\n")
    print(f"reverse_bytes={len(c_source_reverse)}")

    failures = []
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        compiler = pep_c23.compiler_path(compiler_name)
        exe = BUILD / f"seam_chunked_{compiler_name}.exe"
        built = subprocess.run([str(compiler), *extra, "-Wall", "-Wextra", "-Wpedantic",
                                "-Werror", "-O2", str(c_path), "-o", str(exe)],
                               capture_output=True, text=True, check=False)
        if built.returncode:
            stage(f"strict-{compiler_name}", False, built.stderr[:600])
            failures.append(compiler_name)
            continue
        ran = subprocess.run([str(exe)], capture_output=True, check=False)
        out = ran.stdout.replace(b"\r\n", b"\n")
        stage(f"strict-{compiler_name}", True, f"run_stdout={out!r}")
        if out != b"42\n":
            failures.append(f"{compiler_name}-output")
    # Closest valid OCaml oracle: the seed executes top-level statements and ignores `fn main`,
    # while the native entry is the emitter's main wrapper -- the documented entry-point
    # difference. The SAME make_token/let/say calls at top level must print the same value.
    oracle_source = lex_chunk + (
        'fn add_one(v: Int) -> Int {\n'
        '  return v + 1\n'
        '}\n'
        'say(int_text(add_one(41)))\n')
    oracle_path = BUILD / "seam_oracle.pep"
    oracle_path.write_text(oracle_source, encoding="utf-8", newline="\n")
    oracle = subprocess.run([str(A1_SEED), "run", str(oracle_path)], capture_output=True, check=False)
    if oracle.returncode:
        stage("oracle-seed", False, oracle.stderr.decode("utf-8", "replace")[:400])
        failures.append("oracle")
    else:
        oracle_out = oracle.stdout.replace(b"\r\n", b"\n")
        native_exe = BUILD / "seam_chunked_clang.exe"
        if not native_exe.is_file():
            stage("oracle-seed", False,
                  f"seed={oracle_out!r} native=<not built: strict clang compile failed>")
            failures.append("oracle-native-missing")
        else:
            native = subprocess.run([str(native_exe)], capture_output=True, check=False)
            native_out = native.stdout.replace(b"\r\n", b"\n")
            stage("oracle-seed", oracle_out == b"42\n",
                  f"seed={oracle_out!r} native={native_out!r}"
                  " (entry-point difference: seed runs top-level statements, native runs fn main)")
            if oracle_out != native_out:
                failures.append("oracle-mismatch")
    # G-A2-4 reverse-order proof: caller-first assembly must build clean under BOTH strict
    # compilers and print 42, byte-identical to the document-order run above.
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        compiler = pep_c23.compiler_path(compiler_name)
        exe = BUILD / f"seam_reverse_{compiler_name}.exe"
        built = subprocess.run(
            [str(compiler), *extra, "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
             str(c_path_reverse), "-o", str(exe)],
            capture_output=True, text=True, check=False)
        if built.returncode:
            stage(f"strict-rev-{compiler_name}", False, built.stderr[:600])
            failures.append(f"reverse-{compiler_name}")
        else:
            ran = subprocess.run([str(exe)], capture_output=True, check=False)
            out = ran.stdout.replace(b"\r\n", b"\n")
            stage(f"strict-rev-{compiler_name}", out == b"42\n",
                  f"reverse-order run_stdout={out!r}")
            if out != b"42\n":
                failures.append(f"reverse-{compiler_name}-output")

    # ---- G-A2-7: native str_concat (A4 E8 top-ranked R1; source demand = the staged
    # checker's own 13 nested diagnostic-composition sites at A1 @2ad750b, which this
    # session's bundle already carries). One-shot emit through the same session; the bump-pool
    # runtime makes chains, siblings and stale-let aliases sound by construction.
    concat_source = (
        'fn main() -> Int {\n'
        '  let joined = str_concat("hello ", "world")\n'
        '  say(joined)\n'
        '  let chain = str_concat(str_concat("Unknown variable \'", "x"), "\'")\n'
        '  say(chain)\n'
        '  let first = str_concat("buf-1 ", "one")\n'
        '  let second = str_concat("buf-2 ", "two")\n'
        '  let combined = str_concat(first, second)\n'
        '  say(combined)\n'
        '  return 0\n'
        '}\n')
    concat_payload = concat_source.encode("utf-8")
    concat_target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                  "name": "str-concat-fixture", "bytes": list(concat_payload)})
    require(concat_target, "outcome", "ok", "open str-concat fixture")
    concat_sem = {"document": concat_target["document"],
                  "revision": concat_target["revision"], "entryFunctions": []}
    concat_parsed = parse_target(session, concat_payload, concat_target, revision)
    concat_checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_invoke", "tool": "pep-c23-checker",
                                   "arguments": [concat_parsed], "semanticTarget": concat_sem})
    str_concat_ok = concat_checked.get("outcome") == "ok"
    if not str_concat_ok:
        stage("str-concat-check", False, str(concat_checked.get("error"))[:200])
        failures.append("str-concat-check")
    else:
        cstatus = fields_map(concat_checked["result"])["status"]["value"]
        str_concat_ok = cstatus == "valid"
        stage("str-concat-check", str_concat_ok, f"status={cstatus} (A1@pin checker owns the builtin)")
        if not str_concat_ok:
            failures.append("str-concat-check")
    if str_concat_ok:
        emitted = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-emitter",
                                "arguments": [concat_parsed, concat_checked["result"]],
                                "semanticTarget": concat_sem})
        efields = fields_map(emitted["result"]) if emitted.get("outcome") == "ok" else {}
        estatus = efields.get("status", {}).get("value", "")
        csrc = "".join(p["value"] for p in efields.get("sourceParts", {}).get("value", [])) \
            if efields else ""
        emit_ok = emitted.get("outcome") == "ok" and estatus == "emitted" and "pep_str_concat(" in csrc
        stage("str-concat-emit", emit_ok,
              f"status={estatus} bytes={len(csrc)} "
              f"diag={efields.get('diagnostic', {}).get('value', '')[:220]}")
        if not emit_ok:
            failures.append("str-concat-emit")
        else:
            concat_c = BUILD / "seam_str_concat.c"
            concat_c.write_text(csrc, encoding="utf-8", newline="\n")
            # Seed oracle: the SAME statements at top level (seed ignores fn main) -- parity is
            # the whole positive claim; the entry-point difference stays stated as everywhere.
            seed_stmts = concat_source.split("fn main() -> Int {\n", 1)[1].rsplit("}\n", 1)[0]
            seed_stmts = seed_stmts.replace("  return 0\n", "")  # top-level return is invalid
            seed_path = BUILD / "str_concat_seed.pep"
            seed_path.write_text(seed_stmts, encoding="utf-8", newline="\n")
            seed_ran = subprocess.run([str(A1_SEED), "run", str(seed_path)],
                                      capture_output=True, check=False)
            concat_seed = None
            if seed_ran.returncode:
                stage("str-concat-seed", False,
                      seed_ran.stderr.decode("utf-8", "replace")[:200])
                failures.append("str-concat-seed")
            else:
                concat_seed = seed_ran.stdout.replace(b"\r\n", b"\n")
                expected_seed = b"hello world\nUnknown variable 'x'\nbuf-1 onebuf-2 two\n"
                stage("str-concat-seed", concat_seed == expected_seed,
                      f"seed={concat_seed!r}")
                if concat_seed != expected_seed:
                    failures.append("str-concat-seed")
            if concat_seed is not None:
                for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
                    compiler = pep_c23.compiler_path(compiler_name)
                    exe = BUILD / f"seam_str_concat_{compiler_name}.exe"
                    built = subprocess.run(
                        [str(compiler), *extra, "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
                         str(concat_c), "-o", str(exe)],
                        capture_output=True, text=True, check=False)
                    if built.returncode:
                        stage(f"str-concat-{compiler_name}", False, built.stderr[:500])
                        failures.append(f"str-concat-{compiler_name}")
                    else:
                        ran = subprocess.run([str(exe)], capture_output=True, check=False)
                        out = ran.stdout.replace(b"\r\n", b"\n")
                        expected = concat_seed + b"0\n"
                        stage(f"str-concat-{compiler_name}", out == expected,
                              f"run_stdout={out!r}")
                        if out != expected:
                            failures.append(f"str-concat-{compiler_name}-output")
    # Capacity negative: doubling past PEP_STR_CONCAT_CAPACITY must fail closed at RUNTIME.
    # (Deliberately NOT seed-compared: the seed builtin is unbounded -- this is the documented
    # semantic divergence, not a parity claim.)
    # BISECTED 2026-11-04 (three failures, three distinct causes, all measured):
    #   512-/64-/8-byte 16-let chains -> checker STEP_LIMIT: root cause NODE COUNT (~90 nodes)
    #     against the known one-shot ceiling (~55-62, the 66n gate class, A1's lane);
    #   1000-byte base -> LEXER STEP_LIMIT at 210:11: literal byte cost scales per byte.
    # Final shape: capacity 4096, base 160, FIVE lets (~30 nodes, 320 literal bytes): x3=2560
    # passes, x4's right operand (2560) exceeds 4096-2560 -> PEP_RUNTIME_STR_CONCAT_RANGE.
    base = "A" * 160
    neg_lines = ["fn main() -> Int {", f'  let x0 = str_concat("{base}", "{base}")']
    for i in range(1, 5):
        neg_lines.append(f"  let x{i} = str_concat(x{i - 1}, x{i - 1})")
    neg_lines += ["  say(x4)", "  return 0", "}"]
    neg_source = "\n".join(neg_lines) + "\n"
    neg_payload = neg_source.encode("utf-8")
    neg_target = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "str-concat-capacity", "bytes": list(neg_payload)})
    require(neg_target, "outcome", "ok", "open capacity fixture")
    neg_sem = {"document": neg_target["document"],
               "revision": neg_target["revision"], "entryFunctions": []}
    neg_parsed = parse_target(session, neg_payload, neg_target, revision)
    neg_checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [neg_parsed], "semanticTarget": neg_sem})
    neg_check_ok = neg_checked.get("outcome") == "ok"
    if not neg_check_ok:
        stage("str-concat-capacity", False,
              f"check error={str(neg_checked.get('error'))[:200]}")
        failures.append("str-concat-capacity")
    neg_emitted = (session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-emitter",
                                 "arguments": [neg_parsed, neg_checked["result"]],
                                 "semanticTarget": neg_sem})
                   if neg_check_ok else {"outcome": "skipped"})
    neg_fields = fields_map(neg_emitted["result"]) if neg_emitted.get("outcome") == "ok" else {}
    neg_src = "".join(p["value"] for p in neg_fields.get("sourceParts", {}).get("value", [])) \
        if neg_fields else ""
    if not neg_check_ok:
        pass  # failure already recorded with the check error
    elif neg_fields.get("status", {}).get("value") != "emitted" or not neg_src:
        stage("str-concat-capacity", False,
              f"emit status={neg_fields.get('status', {}).get('value')} err={str(neg_emitted.get('error'))[:160]}")
        failures.append("str-concat-capacity")
    else:
        neg_c = BUILD / "seam_str_concat_cap.c"
        neg_c.write_text(neg_src, encoding="utf-8", newline="\n")
        neg_compiler = pep_c23.compiler_path("clang")
        neg_exe = BUILD / "seam_str_concat_cap.exe"
        neg_built = subprocess.run(
            [str(neg_compiler), "-std=c23", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2",
             str(neg_c), "-o", str(neg_exe)],
            capture_output=True, text=True, check=False)
        if neg_built.returncode:
            stage("str-concat-capacity", False, neg_built.stderr[:400])
            failures.append("str-concat-capacity")
        else:
            neg_ran = subprocess.run([str(neg_exe)], capture_output=True, check=False)
            refused = neg_ran.returncode != 0 and b"PEP_RUNTIME_STR_CONCAT_RANGE" in neg_ran.stderr
            stage("str-concat-capacity", refused,
                  f"exit={neg_ran.returncode} stderr={neg_ran.stderr[:80]!r} (capacity divergence, seed unbounded)")
            if not refused:
                failures.append("str-concat-capacity")

    # ---- A2-3 NEGATIVE CONTROLS (Rolling Queue C): every cross-chunk refusal must fail
    # closed with its exact registered diagnostic and emit NOTHING, driven against the exact
    # chunk + report the positive proof used above -- no fabricated fixtures, no hand-written C.
    def report_entry(record, name):
        for entry in record["fields"]:
            if entry["name"] == name:
                return entry
        raise KeyError(name)

    def unit_negative(what, mutate, needle, index=0, expect_error_code=None):
        mutated = json.loads(json.dumps(reports[main_label]))
        if mutate is not None:
            mutate(mutated)
        response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                 "op": "tool_invoke", "tool": "pep-c23-unit",
                                 "arguments": [sliced_by_label[main_label], mutated, typed("Int", index)],
                                 "semanticTarget": sem})
        if response.get("outcome") != "ok":
            error_code = (response.get("error") or {}).get("code")
            if expect_error_code is not None and error_code == expect_error_code:
                # MEASURED: the host session gate rejects arguments from another source
                # revision BEFORE the emitter tool runs, so a stale report never reaches the
                # emitter's own document/revision check (which stays as defence-in-depth for
                # the direct one-shot path). Both layers refuse; neither emits C.
                stage(what, True, f"refused at transport gate code={error_code} (emitter gate not reached)")
                return
            stage(what, False, f"outcome={response.get('outcome')} {str(response.get('error'))[:160]}")
            failures.append(what)
            return
        fields = {f["name"]: f["value"] for f in response["result"]["fields"]}
        status = fields["status"]["value"]
        diagnostic = fields["diagnostic"]["value"]
        empty = not fields["sourceParts"]["value"]
        ok = status == "unsupported" and needle in diagnostic and empty
        stage(what, ok, f"status={status} empty={empty} diag={diagnostic[:110]}")
        if not ok:
            failures.append(what)

    def call_target_entry(mutated):
        calls = report_entry(mutated, "calls")["value"]["value"]
        callee_id = report_entry(calls[0], "calleeId")["value"]["value"]
        for function in report_entry(mutated, "functions")["value"]["value"]:
            if report_entry(function, "semanticId")["value"]["value"] == callee_id:
                return function
        raise KeyError("call target")

    def drop_call_fact(mutated):
        report_entry(mutated, "calls")["value"]["value"] = []

    def duplicate_call_fact(mutated):
        calls = report_entry(mutated, "calls")["value"]["value"]
        calls.append(json.loads(json.dumps(calls[0])))

    def retarget_call(mutated):
        # MEASURED: this protocol encodes Int values as JSON strings -- a raw int -1 was
        # rejected with PEP_TOOL_ARGUMENT_VALUE before the emitter ever ran. Every mutation
        # below therefore PRESERVES the original value's type.
        calls = report_entry(mutated, "calls")["value"]["value"]
        entry = report_entry(calls[0], "calleeId")
        entry["value"]["value"] = "987654" if isinstance(entry["value"]["value"], str) else 987654

    def duplicate_call_target(mutated):
        functions = report_entry(mutated, "functions")["value"]["value"]
        functions.append(json.loads(json.dumps(call_target_entry(mutated))))

    def disagree_arity(mutated):
        entry = report_entry(call_target_entry(mutated), "arity")
        current = entry["value"]["value"]
        bumped = int(current) + 1
        entry["value"]["value"] = str(bumped) if isinstance(current, str) else bumped

    def foreign_result_type(mutated):
        report_entry(call_target_entry(mutated), "returnType")["value"]["value"] = "Str"

    def stale_revision(mutated):
        entry = report_entry(mutated, "revision")
        entry["value"]["value"] = "stale-" + str(entry["value"]["value"])

    unit_negative("neg-no-call-fact", drop_call_fact, "no resolved call fact")
    unit_negative("neg-ambiguous-call", duplicate_call_fact, "ambiguous resolved call facts")
    unit_negative("neg-missing-target", retarget_call, "missing from the checked functions")
    unit_negative("neg-ambiguous-target", duplicate_call_target, "ambiguous in the checked functions")
    unit_negative("neg-arity-mismatch", disagree_arity, "argument count disagrees with the checked arity")
    unit_negative("neg-foreign-result", foreign_result_type,
                  "support Int, Bool, and locally declared record results")
    unit_negative("neg-stale-revision", stale_revision,
                  "do not match the authorised source revision",
                  expect_error_code="PEP_STALE_REVISION")
    unit_negative("neg-unit-index", None, "function unit index is out of range", index=99)

    # G-A2-6 / A1 G-A1-1, exercised from THIS side of the seam: an external fact NAMED like
    # the chunk's own top-level function must be refused by the CHECKER (A1 2ad750b) before any
    # emitter code runs. CONTROL: the ordinary check:add_one stage above already passes with
    # distinct external names on this very chunk, so the refusal discriminates on the name
    # collision alone. One new genuinely discriminating negative, per Campaign G economy.
    duplicate_fact = {"name": "add_one", "arity": 1, "rtype": "Int",
                      "rshape": ("scalar", "", 0),
                      "ptypes": [("Int", ("scalar", "", 0), 0)],
                      "semid": 9700, "synid": 100009700,
                      "node": "0", "start": "0", "end": "0",
                      # A1 727f8af's checked-fact marshallers read document/revision off
                      # the fact itself (F2: checker-stamped at production). This hand-built
                      # negative must carry the SAME authorised target, or it dies on a
                      # KeyError instead of exercising the duplicate-name refusal it exists
                      # to test.
                      "document": sem["document"], "revision": sem["revision"]}
    dup_response = session.send(
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
         "tool": "pep-c23-checker-chunk",
         "arguments": [sliced_by_label["add_one"],
                       {"type": "List[CheckedFunction]",
                        "value": [helper.checked_fn_value(duplicate_fact)]},
                       {"type": "List[ResolvedSignature]",
                        "value": [helper.resolved_sig_value(duplicate_fact)]},
                       {"type": "List[ResolvedTypeDecl]", "value": []},
                       {"type": "Bool", "value": True}],
         "semanticTarget": sem})
    if dup_response.get("outcome") != "ok":
        stage("neg-dup-external-name", False, str(dup_response.get("error"))[:160])
        failures.append("neg-dup-external-name")
    else:
        dup_report = dup_response["result"]
        dup_status = fields_map(dup_report)["status"]["value"]
        dup_codes = [fields_map(entry).get("code", {}).get("value")
                     for entry in (fields_map(dup_report).get("diagnostics", {}).get("value") or [])]
        dup_ok = dup_status == "invalid" and "PEP_DUPLICATE_FUNCTION" in dup_codes
        stage("neg-dup-external-name", dup_ok,
              f"status={dup_status} codes={dup_codes[:3]} (distinct-name control = check:add_one OK)")
        if not dup_ok:
            failures.append("neg-dup-external-name")

    # Assembly-order negative (the measured contract): main's unit BEFORE its callee's unit has
    # no prototype in the declaration-chunk header, so BOTH strict compilers must REFUSE it.
    bad_c = BUILD / "seam_chunked_bad_order.c"
    bad_c.write_text(header + unit_main + unit_add, encoding="utf-8", newline="\n")
    for compiler_name, extra in (("clang", ["-std=c23"]), ("gcc", ["-std=c2x"])):
        built = subprocess.run(
            [str(pep_c23.compiler_path(compiler_name)), *extra, "-Wall", "-Wextra",
             "-Wpedantic", "-Werror", str(bad_c), "-o", str(BUILD / f"seam_bad_{compiler_name}.exe")],
            capture_output=True, text=True, check=False)
        refused = built.returncode != 0 and "pep_fn_add_one" in built.stderr
        stage(f"neg-unit-order-{compiler_name}", refused,
              f"exit={built.returncode} undeclared_callee={'pep_fn_add_one' in built.stderr}")
        if not refused:
            failures.append(f"neg-unit-order-{compiler_name}")
    sys.exit(1 if failures else 0)
finally:
    session.close()
