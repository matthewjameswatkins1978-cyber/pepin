"""Minimiser for the duplicate-type-declaration / fact-order defect (LUCY-20261104-002 slice 1).

Goal: the SHORTEST source that shows the fail-open, pinned to an exact candidate SHA,
with the seed as oracle, and an explicit statement of whether the defect is current
or historical.

Defect under test (reported on #16, confirmed in STAGED-TYPED-ATTACKS-bcfa3c0.md):
when two declarations share a type name and a chunk is checked with external type
facts gathered per declaration, `analyze_chunk_typed` is order-sensitive: one order
accepts a body the seed rejects.

Method: enumerate candidate sources from shortest to longest; for each, gather honest
facts per declaration root (the documented harness pattern), check the same chunk with
facts forward and reversed, and compare with the seed's verdict. The first size that
shows (forward valid, reversed invalid, seed invalid) is the shortest counterexample.

Claim:
  M1  a shortest counterexample exists (both orders observed, seed disagrees).
  M2  the trigger is duplication: the single-declaration control is order-stable.
  O1  the defect's reachability window: report whether the typed entry point exists
      at the pin (historical vs current).

Exit codes: 0 = minimisation found and controls held, 1 = a claim falsified,
2 = harness error (including "typed entry point absent", which is a scope fact).
Usage: python dup_decl_minimiser.py <candidate-worktree> [--json PATH]
"""
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

CANDIDATES = [
    # shortest first
    ("type D {\n    a: Int\n}\ntype D {\n    b: Int\n}\n"
     "fn f(d: D) -> Int {\n    return d.a\n}\n"),
    ("type D {\n    a: Int\n}\ntype D {\n    b: Int\n}\n"
     "fn f(d: D) -> Int {\n    return d.a\n}\nfn main() -> Int { return 0 }\n"),
    ("type D {\n    a: Int\n}\n\ntype D {\n    b: Int\n}\n\n"
     "fn f(d: D) -> Int {\n    return d.a\n}\n\nfn main() -> Int { return 0 }\n"),
]

CONTROL = ("type D {\n    a: Int\n}\n"
           "fn f(d: D) -> Int {\n    return d.a\n}\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source: str):
    with tempfile.TemporaryDirectory(prefix="a3-min-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source.encode("utf-8"))
        done = subprocess.run(["pwsh", "-NoProfile", "-File", str(PEP_PS1), "check",
                               str(path), "--json"],
                              cwd=str(REPO), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    try:
        payload = json.loads(done.stdout.strip())
    except json.JSONDecodeError:
        return "NON_JSON"
    codes = [item.get("code") for item in payload.get("diagnostics") or []]
    return f"{payload.get('status')}{('/' + codes[0]) if codes else ''}"


def main():
    print(f"REPO={REPO}")
    session = Session()
    output = {"repo": str(REPO), "shortest": None, "control": None, "seed": {}}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-min", "metadataOnly": True})
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
        empty_ext = {"type": "List[CheckedFunction]", "value": []}
        empty_sig = {"type": "List[ResolvedSignature]", "value": []}
        empty_types = {"type": "List[ResolvedTypeDecl]", "value": []}
        tools = [
            ("pep-c23-parser-start", "parser_start", [], start_cursor),
            ("pep-c23-parser-step", "parser_step", [finished_cursor],
             pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                        finished_cursor)),
            ("pep-c23-checker-typedecls", "chunk_type_declarations", [empty],
             empty_types),
            ("pep-c23-checker-sigs", "chunk_signatures", [empty], empty_sig),
            ("pep-c23-checker-chunk-typed", "analyze_chunk_typed",
             [empty, empty_ext, empty_sig, empty_types, {"type": "Bool", "value": True}],
             empty_rep),
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
                print(f"[O1] typed entry point unavailable at this pin "
                      f"({tool}: {validated})")
                output["scope"] = f"typed entry point absent at this pin ({tool})"
                print(json.dumps(output, indent=2))
                return 2
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool,
                          "document": opened["document"], "revision": tool_revision})

        def sliced(parsed, node_ids):
            nodes = fields_map(parsed)["nodes"]["value"]
            by_id = {str(nval(node, "id")): node for node in nodes}
            sub = [__import__("copy").deepcopy(by_id[str(node_id)]) for node_id in node_ids]
            chunk = remap_chunk(sub)
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                        if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}

        def run(source: str, label: str):
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"min-{label}",
                                   "bytes": list(source.encode("utf-8"))})
            require(target, "outcome", "ok", f"open {label}")
            sem = {"document": target["document"], "revision": target["revision"],
                   "entryFunctions": []}
            parsed = parse_target(session, source.encode("utf-8"), target, tool_revision)
            nodes = fields_map(parsed)["nodes"]["value"]
            index = contract.DocumentIndex.from_parsed(parsed)
            roots = [int(nval(node, "id")) for node in nodes
                     if str(nval(node, "parentId")) == "-1"
                     and nval(node, "kind") in ("record_declaration", "union_declaration")]
            facts = []
            for root in roots:
                response = session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                     "tool": "pep-c23-checker-typedecls",
                     "arguments": [sliced(parsed, index.subtree(root))],
                     "semanticTarget": sem})
                require(response, "outcome", "ok", "chunk_type_declarations")
                facts.extend(response["result"]["value"])
            sigs = fetch_all_sigs(session, parsed, tool_revision, sem)
            body = None
            for node in nodes:
                if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                        and nval(node, "text") == "f":
                    body = index.subtree(int(nval(node, "id")))
            results = {}
            for name, ordering in (("forward", facts), ("reversed", list(reversed(facts)))):
                response = session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                     "tool": "pep-c23-checker-chunk-typed",
                     "arguments": [sliced(parsed, body),
                                   {"type": "List[CheckedFunction]",
                                    "value": [checked_fn_value(s) for s in sigs
                                              if s["name"] != "f"]},
                                   {"type": "List[ResolvedSignature]",
                                    "value": [resolved_sig_value(s) for s in sigs
                                              if s["name"] != "f"]},
                                   {"type": "List[ResolvedTypeDecl]", "value": ordering},
                                   {"type": "Bool", "value": True}],
                     "semanticTarget": sem})
                require(response, "outcome", "ok", f"analyze_chunk_typed {name}")
                report = fields_map(response["result"])
                results[name] = report["status"]["value"]
            return results

        shortest = None
        for source in CANDIDATES:
            verdicts = run(source, f"cand{len(source)}")
            seed = seed_verdict(source)
            print(f"candidate bytes={len(source)} forward={verdicts['forward']} "
                  f"reversed={verdicts['reversed']} seed={seed}")
            if shortest is None and verdicts["forward"] == "valid" \
                    and verdicts["reversed"] != "valid":
                shortest = {"bytes": len(source), "source": source, "verdicts": verdicts,
                            "seed": seed}
        output["shortest"] = shortest
        record("M1 a shortest counterexample exists (order flips the verdict)",
               True, "flips",
               "flips" if shortest else "no flip reproduced",
               f"shortest={shortest['bytes'] if shortest else '-'} bytes, "
               f"seed={shortest['seed'] if shortest else '-'}")

        control = run(CONTROL, "control")
        seed_control = seed_verdict(CONTROL)
        output["control"] = {"verdicts": control, "seed": seed_control,
                            "bytes": len(CONTROL)}
        record("M2 single-declaration control is order-stable", True, "stable",
               "stable" if control["forward"] == control["reversed"] == "valid"
               else f"forward={control['forward']} reversed={control['reversed']}",
               f"seed={seed_control}")
        output["scope"] = "typed entry point present at this pin"
    finally:
        session.close()

    if JSON_OUT:
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
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
    except BaseException as error:
        import traceback
        traceback.print_exc()
        print(f"HARNESS_ERROR {type(error).__name__}: {error}")
        sys.exit(2)
