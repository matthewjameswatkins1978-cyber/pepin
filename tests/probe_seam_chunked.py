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

A1_SHA = "2f939a0959373c3cafb628e3c8ddfe9b8a6182ff"
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
                           ("pep_ocaml.ml", "a1_seed/pep_ocaml.ml")):
        data = subprocess.run(["git", "show", f"{A1_SHA}:{source}"], cwd=ROOT, check=True,
                              capture_output=True).stdout
        target = BUILD / output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    exe = BUILD / "a1_seed" / "pep.exe"
    if not exe.exists():
        opam_root = os.environ.get("PEPIN_OPAM_ROOT") or str(pathlib.Path.home() / "AppData/Local/opam")
        subprocess.run(["opam", "exec", "--root", opam_root, "--switch", "pepin-5.5.2", "--",
                        "ocamlopt", "-o", str(exe), str(BUILD / "a1_seed" / "pep_ocaml.ml")],
                       cwd=ROOT, check=True)


prepare()
"""Seam demonstration: A1's checked-chunk contract driving MY bounded emitter.

Flow mirrors A1's tests/test_lexer_chunk_ledger.py exactly, at the A1_SHA pin below (2f939a0)
seed + checker with MY emitter in this worktree:

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
    # MEASURED TRANSPORT DEFECT (A1 tests/chunk_helper.py @2f939a0 and @9ad7d95): sigs_from_tool
    # numbers semid = 9000 + i / synid = 1000000000 + i, but fetch_all_sigs parses ONE header
    # chunk per call, so i is 0 every time and every external signature collides at
    # 9000/1000000000. The checker keys CheckedFunction/ResolvedSignature facts by those ids, so
    # with two or more external functions it resolved add_one(41) against make_token's first
    # parameter (Str) and reported PEP_TYPE_MISMATCH on the integer literal (measured here).
    # Renumber in this A2-owned probe; A1's file stays untouched and the ids stay synthetic
    # (never document ids), exactly as the helper's own contract comment requires.
    for signatureIndex, signature in enumerate(sigs):
        signature["semid"] = 9000 + signatureIndex
        signature["synid"] = 1000000000 + signatureIndex
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
    c_source = header + unit_make + unit_add + unit_main + epilogue
    c_path = BUILD / "seam_chunked.c"
    c_path.write_text(c_source, encoding="utf-8", newline="\n")
    print(f"assembled_c_bytes={len(c_source)}")

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
    sys.exit(1 if failures else 0)
finally:
    session.close()
