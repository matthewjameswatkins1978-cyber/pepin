"""Supply-time fn-name collision gate (R-ID-1, A1 52cb397) — differential probe.

A1's Primary-2 gate in `analyze_chunk_inner_bound` refuses external
CheckedFunction/ResolvedSignature facts that name a function the chunk itself
declares (seed-parity PEP_DUPLICATE_FUNCTION), closing the local-first/no-diagnosis
residual for the names-collide subset (A3 T-CALL-6 class).

Fixed expectations at every pin (T-REC pattern): the pre-gate pin documents the
hole by falsifying; the gated pin must hold. Checker-side only (no emitter unit),
so this runs on repair-branch pins where the seam probe cannot.

Cases:
  R1  parity: a revision declaring `dup` twice; chunk = first dup, externals carry
      dup (from the whole-parse sigs). Seed oracle: invalid/PEP_DUPLICATE_FUNCTION.
      Staged must refuse with PEP_DUPLICATE_FUNCTION (pre-gate: valid = hole).
  R2  S4/O4-shape for fn facts: ONE `dup` in source; externals are dup's own
      producer-made values supplied as external (self-consistent forgery naming the
      local fn). Seed oracle: valid (single declaration). Post-gate the rule still
      refuses on name collision — stated rule behavior, NOT seed parity. Pre-gate
      this is admitted (valid). Non-colliding forgeries (true S4/O4: externals name
      only other fns) are untouched by R-ID-1 and remain admissible — see T-ADM-4.
  R3  honest control: same chunk, externals name only OTHER functions -> valid.

Exit codes: 0 = all claims held, 1 = a claim falsified (hole / regression),
2 = harness error / typed entry point absent.
Usage: python fn_collision_gate.py <candidate-worktree> [--json PATH]
"""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile

ARGS = [item for item in sys.argv[1:] if not item.startswith("--")]
REPO = pathlib.Path(ARGS[0] if ARGS else ".").resolve()
JSON_OUT = None
if "--json" in sys.argv:
    JSON_OUT = pathlib.Path(sys.argv[sys.argv.index("--json") + 1])
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402
import pep_chunk_contract as contract  # noqa: E402
from tests.chunk_helper import checked_fn_value, fields_map, nval, remap_chunk  # noqa: E402
from tests.chunk_helper import fetch_all_sigs, resolved_sig_value  # noqa: E402

PEP_PS1 = REPO / "pep.ps1"
RESULTS = []

TWO_DUP = ("fn dup() -> Int {\n    return 1\n}\n"
           "fn dup() -> Int {\n    return 2\n}\n"
           "fn main() -> Int { return 0 }\n")
ONE_DUP = ("fn dup() -> Int {\n    return 1\n}\n"
           "fn main() -> Int { return 0 }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-fncoll-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source.encode("utf-8"))
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"], cwd=str(REPO), capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def main():
    print(f"REPO={REPO}")
    session = Session()
    output = {"repo": str(REPO), "cases": {}}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-fncoll", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        tool_revision = opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                     done=True, lex_done=True,
                                                     lex_stage="done")
        empty = pep_c23.parser_progress(sample["document"], sample["revision"])
        empty_rep = pep_c23.checker_report(sample["document"], sample["revision"])
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty],
             {"type": "List[ResolvedSignature]", "value": []}),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty, {"type": "List[CheckedFunction]", "value": []},
              {"type": "List[ResolvedSignature]", "value": []},
              {"type": "List[ResolvedTypeDecl]", "value": []},
              {"type": "Bool", "value": True}], empty_rep),
        ]
        for tool, function, arguments, expect in tools:
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                          "tool": tool, "document": opened["document"],
                          "revision": tool_revision, "function": function})
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": opened["document"],
                                      "revision": tool_revision,
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            if validated.get("status") != "Validated":
                print(f"[scope] typed entry point unavailable ({tool}: {validated})")
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_activate",
                          "tool": tool, "document": opened["document"],
                          "revision": tool_revision})

        def sliced(parsed, node_ids):
            nodes = fields_map(parsed)["nodes"]["value"]
            by_id = {str(nval(node, "id")): node for node in nodes}
            sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in node_ids]
            chunk = remap_chunk(sub)
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                        if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}

        def run(source, label, chunk_fn, external_names):
            """Chunk = subtree of the first top-level fn named chunk_fn; externals =
            sigs/fns (whole-parse values) filtered to external_names (None = all)."""
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"x-{label}",
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open {label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, tool_revision)
            nodes = fields_map(parsed)["nodes"]["value"]
            index = contract.DocumentIndex.from_parsed(parsed)
            fn_id = None
            for node in nodes:
                if nval(node, "kind") == "function" and \
                        str(nval(node, "parentId")) == "-1" and \
                        nval(node, "text") == chunk_fn:
                    fn_id = int(nval(node, "id"))
                    break
            if fn_id is None:
                return {"verdict": f"NO-FN-{chunk_fn}", "codes": []}
            sigs = fetch_all_sigs(session, parsed, tool_revision, sem)
            keep = [s for s in sigs
                    if external_names is None or s["name"] in external_names]
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [sliced(parsed, index.subtree(fn_id)),
                               {"type": "List[CheckedFunction]",
                                "value": [checked_fn_value(s) for s in keep]},
                               {"type": "List[ResolvedSignature]",
                                "value": [resolved_sig_value(s) for s in keep]},
                               {"type": "List[ResolvedTypeDecl]", "value": []},
                               {"type": "Bool", "value": True}],
                 "semanticTarget": sem})
            require(response, "outcome", "ok", "analyze_chunk_typed")
            report = fields_map(response["result"])

            def field_value(record, name):
                value = fields_map(record).get(name) if isinstance(record, dict) else None
                return value.get("value") if isinstance(value, dict) else value

            diagnostics = report["diagnostics"]["value"] if isinstance(
                report.get("diagnostics"), dict) else []
            return {"verdict": report["status"]["value"],
                    "codes": [field_value(item, "code") for item in diagnostics]}

        def check(label, result, seed, expect_code=True):
            codes = result["codes"] or []
            if expect_code:
                hit = result["verdict"] != "valid" and "PEP_DUPLICATE_FUNCTION" in codes
                return ("refused+PEP_DUPLICATE_FUNCTION" if hit
                        else f"verdict={result['verdict']} codes={codes}")
            return result["verdict"]

        # R1 parity: two-dup revision; chunk + externals collide on `dup`.
        try:
            r1 = run(TWO_DUP, "twodup", "dup", None)
            seed1 = seed_verdict(TWO_DUP)
            record("R1 two-dup revision refuses with PEP_DUPLICATE_FUNCTION", True,
                   "refused+PEP_DUPLICATE_FUNCTION", check("R1", r1, seed1),
                   f"seed={seed1}")
            output["cases"]["R1"] = {"result": r1, "seed": seed1}
        except BaseException as error:  # noqa: BLE001
            record("R1 two-dup revision refuses with PEP_DUPLICATE_FUNCTION", False,
                   "refused+PEP_DUPLICATE_FUNCTION",
                   f"harness: {type(error).__name__}: {error}")

        # R2 S4/O4-shape for fn facts: one dup in source, self-consistent forged
        # external naming the local fn. Seed is valid (single declaration); the
        # post-gate refusal is rule behavior (collision refuses regardless), the
        # pre-gate admission is the documented hole for this subset.
        try:
            r2 = run(ONE_DUP, "onedup", "dup", ["dup", "main"])
            seed2 = seed_verdict(ONE_DUP)
            record("R2 forged external naming the local fn is refused", True,
                   "refused+PEP_DUPLICATE_FUNCTION", check("R2", r2, seed2),
                   f"seed={seed2} (seed-valid by construction; refusal is rule "
                   f"behavior, not parity)")
            output["cases"]["R2"] = {"result": r2, "seed": seed2}
        except BaseException as error:  # noqa: BLE001
            record("R2 forged external naming the local fn is refused", False,
                   "refused+PEP_DUPLICATE_FUNCTION",
                   f"harness: {type(error).__name__}: {error}")

        # R3 honest control: same chunk, externals name only other functions.
        try:
            r3 = run(ONE_DUP, "honest", "dup", ["main"])
            seed3 = seed_verdict(ONE_DUP)
            record("R3 honest externals (no collision) stay valid", True, "valid",
                   check("R3", r3, seed3, expect_code=False),
                   f"seed={seed3}")
            output["cases"]["R3"] = {"result": r3, "seed": seed3}
        except BaseException as error:  # noqa: BLE001
            record("R3 honest externals (no collision) stay valid", False, "valid",
                   f"harness: {type(error).__name__}: {error}")
    finally:
        session.close()

    if JSON_OUT:
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(output, indent=2, sort_keys=True, default=str),
                            encoding="utf-8")
        print(f"json={JSON_OUT}")
    print("\n" + json.dumps(RESULTS, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY claims={len(RESULTS)} claim_falsified={len(falsified)}")
    return 1 if falsified else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
