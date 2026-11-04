"""Cross-chunk duplicate-type attack at a repaired pin (LUCY-20261104-007, A3 slice after A1's 448c689).

A1 closed the duplicate-declaration fail-open inside one chunk
(`duplicateType: contains(duplicateNames, ...)` + `PEP_DUPLICATE_TYPE` guards). These cases ask the
question that repair does NOT answer by itself: what happens when the two declarations of one name
arrive through different chunks, and does the repair over-refuse distinct names?

Cases:
  X1  control: two DISTINCT records with identical fields stay valid (no over-refusal)
  X2  cross-chunk duplicate: `type D {a: Int}` chunk + `type D {b: Int}` chunk, body uses d.a.
      Seed oracle: invalid/PEP_DUPLICATE_TYPE for the whole source.
  X3  cross-chunk duplicate across kinds: record D in one chunk, union D in another
  X4  positive control: both declarations in ONE chunk must be refused or flagged duplicate

Exit codes: 0 = all claims held, 1 = a claim falsified (a hole), 2 = harness error / typed entry point absent.
Usage: python dup_decl_cross_chunk.py <candidate-worktree> [--json PATH]
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

TWO_KINDS = ("type D {\n    a: Int\n}\ntype D = Left() | Right()\n"
             "fn f(d: D) -> Int {\n    return d.a\n}\n")
RENAMED_KINDS = ("type E {\n    a: Int\n}\ntype F = Left() | Right()\n"
                 "fn f(e: E) -> Int {\n    return e.a\n}\n")
KINDS_REVERSED = ("type D = Left() | Right()\ntype D {\n    a: Int\n}\n"
                  "fn f(d: D) -> Int {\n    return d.a\n}\n")
UNION_ONLY = ("type F = Left() | Right()\n"
              "fn f(x: F) -> Int {\n    return 0\n}\n")
SHADOW_PRIMITIVE = ("type Int {\n    a: Int\n}\n"
                    "fn f(x: Int) -> Int {\n    return x.a\n}\n")
SHADOW_TWICE = ("type Str {\n    a: Int\n}\ntype Str {\n    b: Int\n}\n"
                "fn f(x: Str) -> Int {\n    return x.a\n}\n")
DISTINCT = ("type A {\n    x: Int\n}\ntype B {\n    x: Int\n}\n"
            "fn f(a: A) -> Int {\n    return a.x\n}\n")
DUP_SAME_CHUNK = ("type D {\n    a: Int\n}\ntype D {\n    b: Int\n}\n"
                  "fn f(d: D) -> Int {\n    return d.a\n}\n")
DUP_SPLIT = ("type D {\n    a: Int\n}\ntype D {\n    b: Int\n}\n"
             "fn f(d: D) -> Int {\n    return d.a\n}\n")


def record(case, claim, expect, outcome, detail=""):
    falsified = bool(claim and outcome != expect)
    RESULTS.append({"case": case, "claimed": claim, "expect": expect, "outcome": outcome,
                    "detail": detail, "falsified": falsified})
    print(f"[{case}] {'FALSIFIED' if falsified else 'HELD'} -> {outcome}"
          + (f"   ({detail})" if detail else ""))


def seed_verdict(source):
    with tempfile.TemporaryDirectory(prefix="a3-xdup-") as folder:
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
                               "name": "a3-xdup", "metadataOnly": True})
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
            ("pep-c23-checker-typedecls", "chunk_type_declarations", [empty],
             {"type": "List[ResolvedTypeDecl]", "value": []}),
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
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool,
                          "document": opened["document"], "revision": tool_revision})

        def sliced(parsed, node_ids):
            nodes = fields_map(parsed)["nodes"]["value"]
            by_id = {str(nval(node, "id")): node for node in nodes}
            sub = [copy.deepcopy(by_id[str(node_id)]) for node_id in node_ids]
            chunk = remap_chunk(sub)
            return {"type": "ParserProgress", "fields": [
                {"name": key, "value": ({"type": "List[FlatAstNode]", "value": chunk}
                                        if key == "nodes" else fields_map(parsed)[key])}
                for key in [field["name"] for field in parsed["fields"]]]}

        def run(source, label, per_chunk=True):
            """per_chunk=True -> one fact batch per declaration root (the split path)."""
            target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                   "name": f"x-{label}",
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
            batches = []
            groups = [[root] for root in roots] if per_chunk else [roots]
            for group in groups:
                ids = []
                for root in group:
                    ids.extend(index.subtree(root))
                response = session.send(
                    {"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_invoke",
                     "tool": "pep-c23-checker-typedecls",
                     "arguments": [sliced(parsed, ids)], "semanticTarget": sem})
                require(response, "outcome", "ok", "chunk_type_declarations")
                batches.append(response["result"]["value"])
            facts = [fact for batch in batches for fact in batch]
            sigs = fetch_all_sigs(session, parsed, tool_revision, sem)
            body = None
            for node in nodes:
                if nval(node, "kind") == "function" and str(nval(node, "parentId")) == "-1" \
                        and nval(node, "text") == "f":
                    body = index.subtree(int(nval(node, "id")))
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
                               {"type": "List[ResolvedTypeDecl]", "value": facts},
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
                    "codes": [field_value(item, "code") for item in diagnostics],
                    "messages": [field_value(item, "message") for item in diagnostics],
                    "duplicateFlags": [[field_value(fact, "duplicateType")
                                        for fact in batch] for batch in batches],
                    "facts": len(facts)}

        # X1 control: distinct names, identical fields -> must stay valid, no over-refusal
        x1 = run(DISTINCT, "distinct")
        seed1 = seed_verdict(DISTINCT)
        record("X1 control: distinct same-shape records stay valid", True, "valid",
               x1["verdict"], f"seed={seed1} duplicateFlags={x1['duplicateFlags']}")
        output["cases"]["X1"] = {"result": x1, "seed": seed1}

        # X2 cross-chunk duplicate: each declaration in its own chunk
        x2 = run(DUP_SPLIT, "split")
        seed2 = seed_verdict(DUP_SPLIT)
        record("X2 cross-chunk duplicate must be refused (seed refuses)", True,
               "refused", "refused" if x2["verdict"] != "valid" else "valid",
               f"seed={seed2} duplicateFlags={x2['duplicateFlags']}")
        output["cases"]["X2"] = {"result": x2, "seed": seed2}

        # X4 positive control: both declarations in ONE chunk
        x4 = run(DUP_SAME_CHUNK, "samechunk", per_chunk=False)
        seed4 = seed_verdict(DUP_SAME_CHUNK)
        refused = x4["verdict"] != "valid"
        record("X4 same-chunk duplicate is refused or flagged (repair holds)", True,
               "refused", "refused" if refused else "valid",
               f"seed={seed4} duplicateFlags={x4['duplicateFlags']}")
        output["cases"]["X4"] = {"result": x4, "seed": seed4}

        # X3 kind-mismatch duplicate split across chunks (record D vs union D)
        try:
            x3 = run(TWO_KINDS, "kinds")
            seed3 = seed_verdict(TWO_KINDS)
            record("X3 record/union namesake split across chunks must be refused", True,
                   "refused", "refused" if x3["verdict"] != "valid" else "valid",
                   f"seed={seed3} duplicateFlags={x3['duplicateFlags']}")
            output["cases"]["X3"] = {"result": x3, "seed": seed3}
        except BaseException as error:  # noqa: BLE001
            record("X3 record/union namesake split across chunks must be refused", False,
                   "refused", f"harness: {type(error).__name__}: {error}")
            output["cases"]["X3"] = {"harness_error": str(error)}

        # X5 control: same shape, DIFFERENT names -> duplication is the only variable
        try:
            x5 = run(RENAMED_KINDS, "renamed")
            seed5 = seed_verdict(RENAMED_KINDS)
            record("X5 control: record+union with distinct names stays valid", True, "valid",
                   x5["verdict"], f"seed={seed5} duplicateFlags={x5['duplicateFlags']}")
            output["cases"]["X5"] = {"result": x5, "seed": seed5}
        except BaseException as error:  # noqa: BLE001
            record("X5 control: record+union with distinct names stays valid", False,
                   "valid", f"harness: {type(error).__name__}: {error}")

        # X6 order sensitivity of the kind-mismatch duplicate
        try:
            x6 = run(KINDS_REVERSED, "kindsrev")
            seed6 = seed_verdict(KINDS_REVERSED)
            record("X6 union-then-record namesake must also be refused", True, "refused",
                   "refused" if x6["verdict"] != "valid" else "valid",
                   f"seed={seed6} duplicateFlags={x6['duplicateFlags']}")
            output["cases"]["X6"] = {"result": x6, "seed": seed6}
        except BaseException as error:  # noqa: BLE001
            record("X6 union-then-record namesake must also be refused", False, "refused",
                   f"harness: {type(error).__name__}: {error}")

        # P1/P2 the deliberate primitive-shadow exception: the seed refuses these outright
        for label, source, case in (
                ("P1 record shadowing a primitive name (type Int)", SHADOW_PRIMITIVE,
                 "P1 primitive shadow refused like the seed"),
                ("P2 two records shadowing the same primitive (type Str)", SHADOW_TWICE,
                 "P2 repeated primitive shadow refused like the seed")):
            try:
                result = run(source, case.split()[0])
                seed = seed_verdict(source)
                record(case, True, "refused",
                       "refused" if result["verdict"] != "valid" else "valid",
                       f"seed={seed} facts={result['facts']} "
                       f"duplicateFlags={result['duplicateFlags']} codes={result['codes']}")
                output["cases"][case.split()[0]] = {"result": result, "seed": seed}
            except BaseException as error:  # noqa: BLE001
                record(case, False, "refused", f"harness: {type(error).__name__}: {error}")

        # X7 is a union declaration chunk emittable at all (coverage, not duplication)
        try:
            x7 = run(UNION_ONLY, "uniononly")
            seed7 = seed_verdict(UNION_ONLY)
            record("X7 observation: a union declaration chunk yields a fact", False,
                   "fact-emitted",
                   f"facts={x7['facts']} flags={x7['duplicateFlags']} "
                   f"verdict={x7['verdict']} seed={seed7}")
            output["cases"]["X7"] = {"result": x7, "seed": seed7}
        except BaseException as error:  # noqa: BLE001
            record("X7 observation: a union declaration chunk yields a fact", False,
                   "fact-emitted", f"harness: {type(error).__name__}: {error}")
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
