"""A3 BOOT-A3-049: emit-audit any Pep app - per-function check status and the first refusal.

A reusable instrument: point PEPIN_APP_REL / PEPIN_APP_REV at a committed Pep file and it reports,
per function, whether the chunk checks valid, and the first emission refusal with its exact text.
It does NOT run the generated binary; it answers only "can this be emitted at all".

Built to audit A4's T2 cursor probe pair (examples/dogfood/cursor_kind_v1|v2.pep @ 23e0314), which
is a genuinely compiler-shaped function (while -> if -> if -> if) and therefore a direct test of the
ceiling measured in BOOT-A3-045 (one conditional per loop body).

Run: PEPIN_APP_REL=examples/dogfood/cursor_kind_v1.pep PEPIN_APP_REV=23e0314 python verification/probes/emit_any_049.py
"""
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

APP_REL = os.environ.get("PEPIN_APP_REL", "examples/dogfood/cursor_kind_v1.pep")
APP_REV = os.environ.get("PEPIN_APP_REV", "23e0314")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fm = lambda rec: {f["name"]: f["value"] for f in rec.get("fields", [])}


def main():
    helper = load("ch", ROOT / "tests" / "chunk_helper.py")
    pic = load("pic", ROOT / "tests" / "probe_integration_case.py")
    app = subprocess.run(["git", "-C", str(ROOT), "cat-file", "blob", f"{APP_REV}:{APP_REL}"],
                         capture_output=True, check=False).stdout
    if not app:
        print(f"FAIL: cannot read {APP_REV}:{APP_REL}")
        return 2
    print(f"app: {APP_REL} @ {APP_REV}  {len(app)} bytes")

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

        target = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "emitany",
                               "bytes": list(app)})
        st = target.get("status")
        codes = [d.get("code") for d in (target.get("diagnostics") or [])][:4]
        print(f"host analysis: status={st} {codes}")
        if st != "valid":
            print("RESULT: host analysis refuses this program - not an emitter question")
            return 1
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
            chk = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker-chunk",
                                "arguments": [sl,
                                              {"type": "List[CheckedFunction]",
                                               "value": [helper.checked_fn_value(s) for s in other]},
                                              {"type": "List[ResolvedSignature]",
                                               "value": [helper.resolved_sig_value(s) for s in other]},
                                              {"type": "List[ResolvedTypeDecl]", "value": []},
                                              {"type": "Bool", "value": True}],
                                "semanticTarget": sem})
            if chk.get("outcome") != "ok":
                print(f"  chunk {label:<16} ERROR {(chk.get('error') or {}).get('code')}")
                continue
            rpt = fm(chk["result"])
            dcodes = [fm(x).get("code", {}).get("value")
                      for x in (rpt.get("diagnostics", {}).get("value") or [])]
            print(f"  chunk {label:<16} nodes={len(chunk_nodes):<3} status={rpt['status']['value']:<8} {dcodes[:2]}")
            if rpt["status"]["value"] == "valid":
                reports[label] = chk["result"]
                sliced[label] = sl

        if len(reports) != len(labels):
            print("\nRESULT: REFUSED BY THE CHECKER - not an emitter question")
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
                raise RuntimeError(f"{what}: {ef['diagnostic']['value'][:200]}")
            return "".join(p["value"] for p in ef["sourceParts"]["value"])

        first_label = labels[0]
        for stage, args, what in (
                ("header", [sliced[first_label], reports[first_label], typed("Str", "header")], "header"),
                *[(f"unit {l}", [sliced[l], reports[l], typed("Int", 0)], f"unit {l}") for l in labels],
                ("epilogue", [sliced["main"], reports["main"], typed("Str", "main")], "epilogue")):
            try:
                out = invoke("pep-c23-section" if stage in ("header", "epilogue") else "pep-c23-unit",
                             args, what)
                print(f"  emit {stage:<16} OK ({len(out)} bytes)")
            except RuntimeError as error:
                print(f"  emit {stage:<16} FIRST REFUSAL: {error}")
                print(f"\nRESULT: REFUSED AT EMISSION ({stage})")
                return 1
        print("\nRESULT: FULLY EMITTED - every function lowered")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())