"""External callee-fact attacks (Campaign F A3-F3): shared ids, batch duplicates, schema gap.

A1's stated residual (BOOT-A1-20261104-024): external-vs-external duplicate function
names within one fact batch are not yet refused. A2's measured defect: distinct
externals share synthetic ids 9000/1000000000 (A1 helper fix open). The callee
wire schema (document/revision on CheckedFunction/ResolvedSignature) is still a
proposal — this probe verifies that state live at the candidate pin.

Cases (all at one integrated pin; seed oracles printed, fixed expectations):
  E4  control: caller chunk + TWO honest externals, unique synthetic ids ->
      valid (both pins of behavior: proves the shape works when ids are unique).
  E1  shared-id discriminator: same shape, both externals forced to
      semid=9000/synid=1000000000 (names/arity/types honest). Asserts not-valid:
      colliding identity must not validate. If it validates, the falsification
      documents that synthetic ids are unconsulted on this path (see detail) —
      itself evidence for the schema debate, not a silent pass.
  E2a observation: identical duplicate entries (dup sig twice) in one batch ->
      reported, unclaimed (dedupe-valid and refuse are both defensible).
  E2b contradictory batch: same name, one honest (Int,arity1) + one forged
      (Bool,arity2) -> asserts not-valid (a contradictory batch must never
      validate; cf. A2's own ambiguous-target refusal precedent).
  E3p schema-gap proof: the fetched wire values carry no document/revision
      fields, so a foreign-revision callee fact is UNSTAGEABLE at this pin ->
      reported, unclaimed (evidence for A2's ACK decision, not a behavior fail).

Exit codes: 0 = all claims held, 1 = a claim falsified (hole/repro for A1),
2 = harness error. Observations never falsify.
Usage: python ext_callee_attacks.py <candidate-worktree> [--json PATH]
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

SRC2 = ("fn add_one(x: Int) -> Int {\n    return x\n}\n"
        "fn pick(s: Str) -> Int {\n    return 0\n}\n"
        "fn main() -> Int { return add_one(41) }\n")
DUP1 = ("fn dup(x: Int) -> Int {\n    return x\n}\n"
        "fn main() -> Int { return dup(41) }\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-extcallee-") as folder:
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
                               "name": "a3-extcallee", "metadataOnly": True})
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

        def run(source, label, chunk_fn, sigs):
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
                return {"verdict": f"NO-FN-{chunk_fn}", "codes": []}, sem
            response = session.send(
                {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                 "tool": "pep-c23-checker-chunk-typed",
                 "arguments": [sliced(parsed, index.subtree(fn_id)),
                               {"type": "List[CheckedFunction]",
                                "value": [checked_fn_value(s) for s in sigs]},
                               {"type": "List[ResolvedSignature]",
                                "value": [resolved_sig_value(s) for s in sigs]},
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
                    "codes": [field_value(item, "code") for item in diagnostics]}, sem

        def fetch(source, label):
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"s-{label}",
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open s-{label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, tool_revision)
            return fetch_all_sigs(session, parsed, tool_revision, sem)

        def by_name(sigs, name):
            return [s for s in sigs if s["name"] == name]

        seed2 = seed_verdict(SRC2)
        seedd = seed_verdict(DUP1)

        # E4 control: two honest externals, unique synthetic ids.
        try:
            sigs = fetch(SRC2, "e4")
            ext = by_name(sigs, "add_one") + by_name(sigs, "pick")
            for i, s in enumerate(ext):
                s["semid"] = 9000 + i
                s["synid"] = 1000000000 + i
            r4, _ = run(SRC2, "e4", "main", ext)
            record("E4 honest two-external controls stay valid", True, "valid",
                   r4["verdict"], f"seed={seed2} codes={r4['codes']}")
            output["cases"]["E4"] = {"result": r4, "seed": seed2}
        except BaseException as error:  # noqa: BLE001
            record("E4 honest two-external controls stay valid", False, "valid",
                   f"harness: {type(error).__name__}: {error}")

        # E1 shared-id discriminator: same shape, colliding synthetic ids.
        # Callees are TYPE-DISTINCT (Int vs Str param) so an id-keyed
        # mis-resolution is verdict-observable (cf. A2's measured
        # add_one/make_token mismatch); identical shapes would hide it.
        try:
            sigs = fetch(SRC2, "e1")
            ext = by_name(sigs, "add_one") + by_name(sigs, "pick")
            for s in ext:
                s["semid"] = 9000
                s["synid"] = 1000000000
            r1, _ = run(SRC2, "e1", "main", ext)
            record("E1 colliding synthetic ids must not validate", True, "not-valid",
                   "not-valid" if r1["verdict"] != "valid"
                   else f"VALID (ids unconsulted on this path?) codes={r1['codes']}",
                   f"seed={seed2} codes={r1['codes']}")
            output["cases"]["E1"] = {"result": r1, "seed": seed2}
        except BaseException as error:  # noqa: BLE001
            record("E1 colliding synthetic ids must not validate", False, "not-valid",
                   f"harness: {type(error).__name__}: {error}")

        # E2a observation: identical duplicate entries in one batch.
        try:
            sigs = fetch(DUP1, "e2a")
            dup = by_name(sigs, "dup")
            r2a, _ = run(DUP1, "e2a", "main", dup + copy.deepcopy(dup))
            record("E2a identical duplicate batch entries (observation)", False,
                   "observed",
                   f"verdict={r2a['verdict']} codes={r2a['codes']}",
                   f"seed={seedd}; dedupe-valid and refuse both defensible")
            output["cases"]["E2a"] = {"result": r2a, "seed": seedd}
        except BaseException as error:  # noqa: BLE001
            record("E2a identical duplicate batch entries (observation)", False,
                   "observed", f"harness: {type(error).__name__}: {error}")

        # E2b contradictory batch: same name, honest Int/arity1 + forged Bool/arity2.
        try:
            sigs = fetch(DUP1, "e2b")
            dup = by_name(sigs, "dup")
            forged = copy.deepcopy(dup[0])
            forged["arity"] = 2
            forged["rtype"] = "Bool"
            forged["rshape"] = ("builtin", "Bool", 0)
            forged["ptypes"] = [("Int", ("builtin", "Int", 0), 0),
                                ("Int", ("builtin", "Int", 0), 1)]
            forged["semid"] = 9001
            forged["synid"] = 1000000001
            r2b, _ = run(DUP1, "e2b", "main", dup + [forged])
            record("E2b contradictory batch must not validate", True, "not-valid",
                   "not-valid" if r2b["verdict"] != "valid"
                   else f"VALID with contradictory dup facts codes={r2b['codes']}",
                   f"seed={seedd} codes={r2b['codes']}")
            output["cases"]["E2b"] = {"result": r2b, "seed": seedd}
        except BaseException as error:  # noqa: BLE001
            record("E2b contradictory batch must not validate", False, "not-valid",
                   f"harness: {type(error).__name__}: {error}")

        # E3p schema-gap proof: wire values carry no document/revision fields.
        try:
            sigs = fetch(DUP1, "e3p")
            fn_keys = sorted(item["name"] for item in checked_fn_value(sigs[0])["fields"])
            sig_keys = sorted(item["name"] for item in resolved_sig_value(sigs[0])["fields"])
            gap = "document" not in fn_keys and "revision" not in fn_keys \
                and "document" not in sig_keys and "revision" not in sig_keys
            record("E3p callee facts carry no provenance fields (schema gap)", False,
                   "observed",
                   "identity-free (foreign fn fact unstageable)"
                   if gap else f"fields-changed fn={fn_keys} sig={sig_keys}",
                   f"CheckedFunction fields={fn_keys}; ResolvedSignature fields={sig_keys}")
            output["cases"]["E3p"] = {"fn_fields": fn_keys, "sig_fields": sig_keys}
        except BaseException as error:  # noqa: BLE001
            record("E3p callee facts carry no provenance fields (schema gap)", False,
                   "observed", f"harness: {type(error).__name__}: {error}")
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
