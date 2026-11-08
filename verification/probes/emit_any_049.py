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
    # AUTHORITATIVE VERDICT: the product path, run exactly as a user would (A3-156).
    # Everything below this block drives the legacy `pep-c23-checker-chunk` tool with empty
    # bindings. A1's sectional driver has superseded it with `bound-chunk` carrying bindings,
    # expect_returns and a fact_closure-restricted external set, and the two disagree: this
    # probe reported "REFUSED BY THE CHECKER" on find_brace while the product path reached
    # emission. So the per-function status below is a DIAGNOSTIC. Never quote it as evidence
    # about check or build status - quote this line instead.
    pdir = ROOT / "_build" / "_a3_emitany"
    pdir.mkdir(parents=True, exist_ok=True)
    psrc = pdir / "app.pep"
    psrc.write_bytes(app)
    prod = subprocess.run(
        [sys.executable, str(ROOT / "pep_c23.py"), "build-c23", str(psrc),
         "--sectional", "--output", str(pdir / "app.exe")],
        capture_output=True, text=True, timeout=6000)
    ptxt = (prod.stderr or prod.stdout or "").strip().splitlines()
    print(f"PRODUCT PATH (authoritative): rc={prod.returncode} "
          f"{(ptxt[-1] if ptxt else '(silent)')}")

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
        # Library sources (e.g. examples/pep_lexer.pep) have no `main`; declaring a missing
        # entry yields PEP_SEMANTIC_ROOT_NOT_FOUND from the signature stage. Select the entry
        # only when the source actually defines one.
        entry = ["main"] if b"fn main(" in app else []
        sem = {"document": target["document"], "revision": target["revision"],
               "entryFunctions": entry}
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
                # Node count still matters on refusal: it is the shape the
                # statement-chain path has to cover, so report it here too.
                print(f"  chunk {label:<16} nodes={len(chunk_nodes):<3} ERROR "
                      f"{(chk.get('error') or {}).get('code')}")
                continue
            rpt = fm(chk["result"])
            dcodes = [fm(x).get("code", {}).get("value")
                      for x in (rpt.get("diagnostics", {}).get("value") or [])]
            print(f"  chunk {label:<16} nodes={len(chunk_nodes):<3} status={rpt['status']['value']:<8} {dcodes[:2]}")
            if rpt["status"]["value"] == "valid":
                reports[label] = chk["result"]
                sliced[label] = sl

        if len(reports) != len(labels) and os.environ.get("PEPIN_UNITS_ONLY") != "1":
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

        # A3-S1/S2: PEPIN_UNITS_ONLY=1 measures per-function EMISSION even when some
        # chunks refused the initial check, so the emit side can be reported
        # independently of the check side. Off by default: a full build still
        # requires every function.
        if os.environ.get("PEPIN_UNITS_ONLY") == "1":
            valid = [l for l in labels if l in reports]
            print(f"\npartial mode: {len(valid)}/{len(labels)} checked valid; "
                  f"measuring emission for those only")
            emitted, refused = 0, []
            for label in valid:
                try:
                    out = invoke("pep-c23-unit",
                                 [sliced[label], reports[label], typed("Int", 0)],
                                 f"unit {label}")
                    emitted += 1
                    print(f"  unit {label:<16} EMITTED ({len(out)} bytes)")
                    # A3-S2: per-emission step cost. last_execute_steps overwrites on
                    # each tool_invoke, so read it absolutely right after this call.
                    if os.environ.get("PEPIN_STEPS") == "1":
                        got = session.send({"schemaVersion": 3, "op": "metrics"})
                        steps = (got.get("metrics") or {}).get("last_execute_steps")
                        unit_nodes = len(fm(sliced[label])["nodes"]["value"])
                        print(f"       steps={steps}  nodes={unit_nodes}")
                except RuntimeError as error:
                    refused.append(label)
                    print(f"  unit {label:<16} FIRST REFUSAL: {error}")
            print(f"\nPARTIAL RESULT: {emitted}/{len(valid)} check-valid functions emit")
            if refused:
                print(f"  refused: {', '.join(refused)}")
            return 0

        pieces = []
        first_label = labels[0]
        for stage, args, what in (
                ("header", [sliced[first_label], reports[first_label], typed("Str", "header")], "header"),
                *[(f"unit {l}", [sliced[l], reports[l], typed("Int", 0)], f"unit {l}") for l in labels],
                ("epilogue", [sliced["main"], reports["main"], typed("Str", "main")], "epilogue")):
            try:
                out = invoke("pep-c23-section" if stage in ("header", "epilogue") else "pep-c23-unit",
                             args, what)
                pieces.append(out)
                print(f"  emit {stage:<16} OK ({len(out)} bytes)")
            except RuntimeError as error:
                print(f"  emit {stage:<16} FIRST REFUSAL: {error}")
                print(f"\nRESULT: REFUSED AT EMISSION ({stage})")
                return 1
        print("\nRESULT: FULLY EMITTED - every function lowered")

        # A3-S1: persist the emitted C so a differential audit can compare bytes
        # instead of trusting printed logs. Inactive unless PEPIN_C_OUT is set.
        c_out = os.environ.get("PEPIN_C_OUT")
        if c_out:
            pathlib.Path(c_out).write_text("".join(pieces), encoding="utf-8", newline="\n")
            print(f"  wrote {c_out} ({len(''.join(pieces))} bytes)")

        # optional native stage: PEPIN_RUN_FIXTURES = semicolon-separated input paths
        runs = [p for p in (os.environ.get("PEPIN_RUN_FIXTURES") or "").split(";") if p.strip()]
        if runs:
            import subprocess as sp
            build = ROOT / "_build"
            build.mkdir(parents=True, exist_ok=True)
            c_path = build / "emitany_run.c"
            c_path.write_text("".join(pieces), encoding="utf-8", newline="\n")
            for comp, std in (("clang", "-std=c23"), ("gcc", "-std=c2x")):
                exe = build / f"emitany_run_{comp}.exe"
                cc = sp.run([str(pep_c23.compiler_path(comp)), std, "-Wall", "-Wextra",
                             "-Wpedantic", "-Werror", "-O2", str(c_path), "-o", str(exe)],
                            capture_output=True, text=True, check=False)
                print(f"  build {comp:<6} {'OK' if cc.returncode == 0 else 'FAIL ' + cc.stderr.strip()[:120]}")
                if cc.returncode != 0:
                    continue
                for fx in runs:
                    rr = sp.run([str(exe), fx.strip()], capture_output=True, text=True,
                                check=False)
                    print(f"    run {comp} {fx.strip():<42} -> stdout={rr.stdout.strip()!r} "
                          f"exit={rr.returncode}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())