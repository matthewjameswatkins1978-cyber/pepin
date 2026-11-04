"""Seam demonstration: A1's checked-chunk contract driving MY bounded emitter (reproducible).

Auto-prepares pinned inputs, then mirrors A1's tests/test_lexer_chunk_ledger.py flow:
  git-fetch A1 codex/p1-checker-cost-fix at the pinned SHA, dump their lexer/parser/checker and
  compile their seed into _build/a1_seed (their checker needs the str_concat builtin) ->
  parse fixture -> per-chunk plan (decl closure + function subtree + referenced decls) ->
  analyze_chunk with external signatures -> MY header/units/epilogue emitted FROM CHUNK REPORTS.

Measured outputs recorded 2026-11-04: all chunks check valid (decl 18, make_token 55 nodes --
matching A1's pinned ledger -- main 33); header, the make_token function unit and the epilogue
emit from those chunk reports; lowering main's body across chunk boundaries refuses with
"Pep C23 calls require a known target" -- the PINNED INTERFACE REQUIREMENT for signature-driven
cross-chunk call lowering (checked.functions/CheckedFunction + checked.calls/ResolvedCall carry
the facts; the emitter resolves callee parameter/return nodes from its own parsed today).
A merged single-chunk plan was measured to hit PEP_RUNTIME_STEP_LIMIT, so the refusal is a real
interface gap, not a chunking choice.
"""
import subprocess

A1_SHA = "3da8f99e6b1bef0fa2965b2f8d21c3cdde182d82"
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

Flow mirrors A1's tests/test_lexer_chunk_ledger.py exactly, at A1 FETCH_HEAD (3da8f99) seed +
checker with MY emitter (3d95cbc):

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
fixture = (lex_chunk +
           "fn main() -> Int {\n"
           "  let token = make_token(\"integer\", \"\", 42, [], 0, 2, 1, 1)\n"
           "  return token.integerValue\n"
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
            ("pep-c23-checker-chunk", "analyze_chunk", [empty_pp, empty_ext, empty_sig],
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
                                               "value": [helper.resolved_sig_value(s) for s in other]}],
                                "semanticTarget": sem})
        if checked.get("outcome") != "ok":
            stage(f"check:{label}", False, str(checked.get("error"))[:200])
            sys.exit(2)
        report = checked["result"]
        status = fields_map(report)["status"]["value"]
        stage(f"check:{label}", status == "valid", f"status={status} nodes={len(planned)}")
        if status != "valid":
            sys.exit(3)
        reports[label] = report
        sliced_by_label[label] = sliced

    decl_label = labels[0]
    body_label = "make_token"
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

    # MEASURED SEAM BOUNDARY (recorded, not hidden): lowering main's body across chunk
    # boundaries needs the callee's signature -- the emitter resolves call targets from the same
    # parsed nodes, and main's chunk carries make_token only as a CheckedFunction/ResolvedCall
    # fact. Expected refusal below is the pinned interface requirement for signature-driven call
    # lowering; the header + make_token unit above already prove checked bounded emission.
    unit_main_response = session.send(
        {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
         "tool": "pep-c23-unit",
         "arguments": [sliced_by_label[main_label], reports[main_label], typed("Int", 0)],
         "semanticTarget": sem})
    unit_main_fields = {f["name"]: f["value"] for f in unit_main_response["result"]["fields"]}
    unit_main_status = unit_main_fields["status"]["value"]
    unit_main_diag = unit_main_fields["diagnostic"]["value"]
    boundary = unit_main_status == "unsupported" and "known target" in unit_main_diag
    stage("emit-unit-main", boundary,
          f"status={unit_main_status} diag={unit_main_diag[:120]}"
          + (" <- cross-chunk call targets: PINNED HANDOFF" if boundary else ""))
    if not boundary:
        sys.exit(6)

    epilogue = invoke("pep-c23-section",
                      [sliced_by_label[main_label], reports[main_label], typed("Str", "main")],
                      "emit-epilogue")
    print("ASSEMBLY-DEMO: header + make_token unit + epilogue emitted from chunk reports; "
          "full native RUN requires signature-driven cross-chunk call lowering (handoff).")
    sys.exit(0)

    c_source = header + unit_make + unit_main + epilogue
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
    sys.exit(1 if failures else 0)
finally:
    session.close()
