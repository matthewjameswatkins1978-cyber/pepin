"""A3 BOOT-A3-031: does chunked checking reject ill-typed variants of the real app shape?

Pre-registration: verification/acceptance/PRE-REGISTRATION-A3-031-ILLTYPED-CHUNK-MATRIX.md @ a6ea71f,
committed before this probe existed or ran.

Question: given the pinned frozen application and ONE targeted corruption per variant, does the same
chunked check the mission uses (parse -> per-function chunk -> analyze_chunk_typed with the other
three functions supplied as external facts) refuse each ill-typed variant?

  V0 control : the pinned app itself           -> all four chunks valid
  V1..V6     : one corruption each             -> at least one chunk NOT valid

Any V1..V6 that comes back `valid` is ACCEPTING-INVALID: a soundness failure of the staged layer, and
it outranks any emitter/performance work.

Also checks two new A4 reference claims (continue-byte counts 105/137/0/706, LF counts 3/5/0/39) in
pure Python over committed blob bytes. Those are reference checks, not gates.

Run: python verification/probes/illtyped_chunk_matrix_031.py [--json]
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

PROBE_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT = pathlib.Path(os.environ.get("PEPIN_GATE_ROOT") or PROBE_ROOT).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target, typed  # noqa: E402

APP_REL = "examples/dogfood/pepin-source-scan.pep"
APP_REV = "12e143f"
APP_BLOB = "4a44dd653e949258a196d247097197d7c24c1da7"

# A4's published reference claims (b57d4bf outbox), to verify independently.
A4_CONTINUE = {"input_ascii.pep": 105, "input_nonascii.pep": 137, "input_empty.pep": 0,
               "pepin-source-scan.pep": 706}
A4_LF = {"input_ascii.pep": 3, "input_nonascii.pep": 5, "input_empty.pep": 0,
         "pepin-source-scan.pep": 39}

# Single targeted corruption per variant: (tag, description, old, new)
VARIANTS = [
    ("V1", "ascii_letter returns Int where -> Bool",
     "  return (65 <= byte && byte <= 90) || (97 <= byte && byte <= 122) || byte == 95\n",
     "  return byte\n"),
    ("V2", "main calls ascii_letter(\"x\") - Str for Int",
     "if ascii_letter(byte_at(source, o)) {", "if ascii_letter(\"x\") {"),
    ("V3", "main calls ascii_letter() - wrong arity",
     "if ascii_letter(byte_at(source, o)) {", "if ascii_letter() {"),
    ("V4", "main returns Str for -> Int",
     "  return n\n}", "  return \"s\"\n}"),
    ("V5", "byte_at offset is Str",
     "byte_at(source, o - 1)", "byte_at(source, \"x\")"),
    ("V6", "callee name typo - undeclared function",
     "ascii_letter(byte_at(source, o))", "ascii_lettr(byte_at(source, o))"),
]

IDENT = frozenset(list(range(0x30, 0x3A)) + list(range(0x41, 0x5B)) +
                  list(range(0x61, 0x7B)) + [0x5F])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def blob_bytes(rel):
    raw = subprocess_run(["git", "-C", str(ROOT), "cat-file", "blob", f"{APP_REV}:{rel}"])
    if raw is None:
        raise RuntimeError(f"cannot read blob {APP_REV}:{rel}")
    return raw


def subprocess_run(argv):
    import subprocess
    done = subprocess.run(argv, capture_output=True, check=False)
    return done.stdout if done.returncode == 0 else None


class Gate:
    def __init__(self):
        self.rows = []

    def row(self, name, ok, detail):
        self.rows.append({"check": name, "ok": bool(ok), "detail": detail})


def check_all_chunks(session, helper, revision, sem, payload, label):
    """Chunk every function in `payload` and check each with the others as external facts."""
    parsed = parse_target(session, payload, {"document": sem["document"],
                                             "revision": sem["revision"]}, revision)
    pfields = fm(parsed)
    nodes = pfields["nodes"]["value"]
    index = __import__("pep_chunk_contract").DocumentIndex.from_parsed(parsed)
    try:
        sigs = helper.fetch_all_sigs(session, parsed, revision, sem)
    except Exception as error:                     # noqa: BLE001 - refusal is a valid outcome
        return None, f"signature fetch refused: {error}"
    labels = [helper.nval(n, "text") for n in nodes if helper.nval(n, "kind") == "function"]
    results = {}
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
        resp = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                             "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                             "arguments": [sl,
                                           {"type": "List[CheckedFunction]",
                                            "value": [helper.checked_fn_value(s) for s in other]},
                                           {"type": "List[ResolvedSignature]",
                                            "value": [helper.resolved_sig_value(s) for s in other]},
                                           {"type": "List[ResolvedTypeDecl]", "value": []},
                                           {"type": "Bool", "value": True}],
                             "semanticTarget": sem})
        if resp.get("outcome") != "ok":
            results[label] = ("error", [str((resp.get("error") or {}).get("code"))])
            continue
        f = fm(resp["result"])
        codes = [fm(x).get("code", {}).get("value")
                 for x in (f.get("diagnostics", {}).get("value") or [])]
        results[label] = (f["status"]["value"], codes)
    return results, None


def main():
    as_json = "--json" in sys.argv
    gate = Gate()
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")

    app_bytes = blob_bytes(APP_REL)
    app_sha = hashlib.sha256(app_bytes).hexdigest()
    gate.row("app:pinned", app_sha.startswith("f6e8f942") and len(app_bytes) == 1159,
             f"sha256={app_sha[:16]} bytes={len(app_bytes)} expected blob {APP_BLOB[:8]}")
    text = app_bytes.decode("utf-8")

    # ---- A4's two reference claims, pure Python over committed bytes ---------
    for name, claimed in A4_CONTINUE.items():
        data = app_bytes if name == "pepin-source-scan.pep" else blob_bytes(
            f"examples/dogfood/{name}")
        got = sum(1 for b in data if b in IDENT)
        gate.row(f"a4-continue-bytes:{name}", got == claimed,
                 f"a4_claims={claimed} a3_oracle={got} bytes={len(data)}")
    for name, claimed in A4_LF.items():
        data = app_bytes if name == "pepin-source-scan.pep" else blob_bytes(
            f"examples/dogfood/{name}")
        got = data.count(10)
        gate.row(f"a4-lf-count:{name}", got == claimed,
                 f"a4_claims={claimed} a3_oracle={got}")

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

        cases = [("V0", "control - the pinned app unmodified", app_bytes)]
        for tag, desc, old, new in VARIANTS:
            if text.count(old) != 1:
                gate.row(f"{tag}:buildable", False,
                         f"substitution string occurs {text.count(old)}x, expected 1")
                continue
            cases.append((tag, desc, text.replace(old, new).encode("utf-8")))

        gate.row("matrix:cases-built", len(cases) == 1 + len(VARIANTS),
                 f"{len(cases)} cases built: {[c[0] for c in cases]}")
        table = []
        for tag, desc, payload in cases:
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"illtyped-{tag}", "bytes": list(payload)})
            if target.get("outcome") != "ok":
                error = (target.get("error") or {}).get("code")
                gate.row(f"{tag}:LAYER-open", False,
                         f"open itself errored: {error}")
                table.append((tag, desc, None, f"open error: {error}"))
                continue
            status = target.get("status")
            host_codes = [d.get("code") for d in (target.get("diagnostics") or [])][:4]

            if tag == "V0":
                gate.row("V0:control-status-valid", status == "valid",
                         f"pinned app open_bytes status={status} diagnostics={host_codes}")
                if status != "valid":
                    table.append((tag, desc, None, "control is not valid; run meaningless"))
                    continue

            # Ill-typed variants: if the HOST analysis already refuses, the per-chunk Pep
            # checker is never reached. Attribute the layer instead of calling it a chunk result.
            if tag != "V0" and status != "valid":
                gate.row(f"{tag}:LAYER-host-analysis", True,
                         f"REFUSED BY HOST ANALYSIS at open_bytes (status={status}, "
                         f"codes={host_codes}); the per-chunk Pep checker was NOT reached, so "
                         f"this row is fail-closed but is not evidence about chunk-level typing")
                table.append((tag, desc, False,
                              f"host-analysis refusal status={status} {host_codes}"))
                continue

            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": ["main"]}
            results, error = check_all_chunks(session, helper, revision, sem, payload, tag)
            if results is None:
                gate.row(f"{tag}:LAYER-signatures", True,
                         f"REFUSED AT SIGNATURE STAGE: {error} -- fail-closed, but the "
                         f"chunk-level type check was still not exercised")
                table.append((tag, desc, False, f"refused at signatures: {error}"))
                continue
            all_valid = all(s == "valid" for s, _ in results.values())
            detail = "; ".join(f"{k}={v[0]}{v[1] if v[0] != 'valid' else ''}"
                               for k, v in results.items())
            if tag == "V0":
                gate.row("V0:control-all-chunks-valid", all_valid,
                         "control holds: all four chunks valid" if all_valid
                         else "CONTROL FAILED: " + detail)
            elif all_valid:
                gate.row(f"{tag}:LAYER-chunk-checker", False,
                         "ACCEPTING-INVALID by the per-chunk checker! " + detail)
            else:
                gate.row(f"{tag}:LAYER-chunk-checker", True,
                         "REFUSED BY THE PER-CHUNK CHECKER: " + detail)
            table.append((tag, desc, all_valid, detail))
    finally:
        session.close()

    if not as_json:
        print("\nvariant summary (description / all-chunks-valid / detail)")
        for tag, desc, all_valid, detail in table:
            state = "ALL-VALID" if all_valid else "rejected"
            print(f"  {tag:4} {state:12} {desc[:44]:44} {detail[:70]}")

    ok = all(r["ok"] for r in gate.rows)
    if as_json:
        print(json.dumps({"verdict": "SOUND" if ok else "SOUNDNESS-FAILURE",
                          "checks": gate.rows}, indent=2))
    else:
        for r in gate.rows:
            print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<34} {r['detail']}")
        failed = [r["check"] for r in gate.rows if not r["ok"]]
        print(f"\n{len(gate.rows)} checks, {len(gate.rows) - len(failed)} passed")
        print("staged checker, ill-typed matrix:", "SOUND" if ok else f"FAILURE {failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
