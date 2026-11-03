"""Which checker pass burns the budget? — attribute cost by measuring each pass separately.

The cost profile showed the checker's ceiling is shape-dependent (36 nodes for match
arms, 104 for record declarations). This probe asks *where* that cost lives, without
editing any builder file: each exported checker pass is registered as its own tool and
laddered over the same shape families, all under the same fixed 100,000-step budget.

Passes measured (all take the same `ParserProgress` argument):
  analyze_parsed           the whole Pep-written checker
  chunk_signatures         `resolve_all_signatures` over the parsed tree
  chunk_type_declarations  the slice-4a record-fact producer

Claims:
  A1  control: the whole checker's ceiling differs materially between the cheapest
      and most expensive shape (the profile's finding, restated here).
  A2  at least one sub-pass survives beyond the whole checker's ceiling on the
      expensive shape — i.e. the cost is concentrated in what the whole checker does
      that this pass does not.
  A3  no sub-pass is *below* the whole checker's ceiling by more than 2x on the
      cheapest shape (a sub-pass should not be the sole bottleneck there).
  O1  the ordering of sub-pass ceilings on the expensive shape is recorded, so the
      attribution is data, not a story.

Local measurement only; no builder file is modified and nothing is published.

Exit codes: 0 = attribution produced and claims held, 1 = a claim falsified,
2 = harness error.
Usage: python checker_pass_attribution.py <tree-with-checker> [max_rung]
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_RUNG = int(sys.argv[2]) if len(sys.argv) > 2 else 32
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

PASSES = {
    "analyze_parsed": ("pep-c23-checker", "checker-report"),
    "chunk_signatures": ("pep-c23-signatures", "list"),
    "chunk_type_declarations": ("pep-c23-typefacts", "list"),
}


def shape_lets(n):
    return ("\n".join(f"let a{i} = {i};" for i in range(n)) + "\n").encode()


def shape_bool_chains(n):
    body = [f"fn b{i}(x: Int) -> Bool {{\n"
            f"  return x == {i} && x == {i + 1} || x == {i + 2} || x == {i + 3}\n"
            f"}}" for i in range(n)]
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def shape_records(n):
    body = [f"type R{i} {{\n    a: Int\n    b: Int\n}}" for i in range(n)]
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def shape_match_arms(n):
    variants = " | ".join(f"V{i}(Int)" for i in range(n))
    arms = "\n        ".join(f"V{i}(value) => value" for i in range(n))
    return (f"type E = {variants}\n\nfn pick(e: E) -> Int {{\n"
            f"    return match e {{\n        {arms}\n    }}\n}}\n\n"
            f"fn main() -> Int {{ return 0 }}\n").encode()


SHAPES = {
    "lets": shape_lets,
    "records": shape_records,
    "bool_chains": shape_bool_chains,
    "match_arms": shape_match_arms,
}

LADDER = [2, 4, 8, 12, 16, 20, 24, 28, 32, 40]


def register_all(session, opened, sample):
    target_spec = {"document": sample["document"], "revision": sample["revision"],
                   "entryFunctions": []}
    start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
    finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                 done=True, lex_done=True, lex_stage="done")
    empty = pep_c23.parser_progress(sample["document"], sample["revision"])
    vectors = [
        ("pep-c23-parser-start", "parser_start", [], start_cursor),
        ("pep-c23-parser-step", "parser_step", [finished_cursor],
         pep_c23.parser_chunk_value(sample["document"], sample["revision"], finished_cursor)),
        ("pep-c23-checker", "analyze_parsed", [empty],
         pep_c23.checker_report(sample["document"], sample["revision"])),
        ("pep-c23-signatures", "chunk_signatures", [empty],
         {"type": "List[ResolvedSignature]", "value": []}),
        ("pep-c23-typefacts", "chunk_type_declarations", [empty],
         {"type": "List[ResolvedTypeDecl]", "value": []}),
    ]
    for tool, function, arguments, expect in vectors:
        registered = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                   "op": "tool_register", "tool": tool,
                                   "document": opened["document"],
                                   "revision": opened["revision"],
                                   "function": function})
        require(registered, "status", "Registered", f"register {tool}")
        validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_validate", "tool": tool,
                                  "document": opened["document"],
                                  "revision": opened["revision"],
                                  "testVectors": [{"arguments": arguments, "expect": expect,
                                                   "semanticTarget": target_spec}]})
        require(validated, "status", "Validated", f"validate {tool}: {validated}")
        activated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                  "op": "tool_activate", "tool": tool,
                                  "document": opened["document"],
                                  "revision": opened["revision"]})
        require(activated, "status", "Active", f"activate {tool}")


def main():
    print(f"REPO={REPO}")
    session = Session()
    profile = {}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-pass-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        register_all(session, opened, sample)

        for shape, generator in SHAPES.items():
            rows = []
            for rung in LADDER:
                if rung > MAX_RUNG:
                    continue
                source = generator(rung)
                target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": f"a3-pass-{shape}-{rung}",
                                       "bytes": list(source)})
                require(target, "outcome", "ok", "open payload")
                try:
                    parsed = parse_target(session, source, target, opened["revision"])
                except BaseException as error:  # noqa: BLE001
                    rows.append({"rung": rung, "bytes": len(source),
                                 "units": None, "state": f"PARSE:{str(error)[:40]}",
                                 "passes": {}})
                    continue
                nodes = 0
                for field in parsed["fields"]:
                    if field["name"] == "nodes":
                        nodes = len(field["value"]["value"])
                states = {}
                for name, (tool, _kind) in PASSES.items():
                    response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                             "op": "tool_invoke", "tool": tool,
                                             "arguments": [parsed],
                                             "semanticTarget": {
                                                 "document": target["document"],
                                                 "revision": target["revision"],
                                                 "entryFunctions": []}})
                    states[name] = ("ok" if response.get("outcome") == "ok"
                                    else (response.get("error") or {}).get("code"))
                rows.append({"rung": rung, "bytes": len(source), "units": nodes,
                             "state": "ok" if states["analyze_parsed"] == "ok" else "refused",
                             "passes": states})
                print(f"{shape:<12} rung={rung:>3} bytes={len(source):>5} nodes={nodes:>4} "
                      + " ".join(f"{name}={state}" for name, state in states.items()))
            profile[shape] = rows
    finally:
        session.close()

    def ceiling(rows, name):
        ok = [row for row in rows if row["passes"].get(name) == "ok"]
        return (max(ok, key=lambda row: row["rung"])["units"] if ok else 0)

    print("\n== ceilings (nodes at last success) ==")
    table = {}
    for shape, rows in profile.items():
        table[shape] = {name: ceiling(rows, name) for name in PASSES}
        print(f"{shape:<12} " + " ".join(f"{name}={table[shape][name]}" for name in PASSES))

    RESULTS = []
    whole = {shape: table[shape]["analyze_parsed"] for shape in table}
    cheapest = max(whole, key=whole.get)
    priciest = min(whole, key=whole.get)
    ratio = whole[cheapest] / max(whole[priciest], 1)
    RESULTS.append({"case": "A1 control: whole-checker ceiling varies by shape",
                    "claimed": True, "expect": "ratio>=1.5", "falsified": ratio < 1.5,
                    "outcome": f"cheapest={cheapest}({whole[cheapest]}) "
                               f"priciest={priciest}({whole[priciest]}) ratio={ratio:.2f}"})
    sub_best = max(table[priciest][name] for name in PASSES if name != "analyze_parsed")
    claim_a2 = sub_best > whole[priciest]
    RESULTS.append({"case": "A2 a sub-pass survives beyond the whole checker on the "
                            "expensive shape", "claimed": True, "expect": "sub>whole",
                    "falsified": not claim_a2,
                    "outcome": f"{priciest}: whole={whole[priciest]} best_sub={sub_best} "
                               f"{json.dumps(table[priciest])}"})
    cheap_subs = {name: table[cheapest][name] for name in PASSES if name != "analyze_parsed"}
    worst_cheap = min(cheap_subs.values()) if cheap_subs else 0
    claim_a3 = worst_cheap * 2 >= table[cheapest]["analyze_parsed"]
    RESULTS.append({"case": "A3 no sub-pass is <2x the whole checker on the cheapest shape",
                    "claimed": True, "expect": "within 2x", "falsified": not claim_a3,
                    "outcome": f"{cheapest}: whole={table[cheapest]['analyze_parsed']} "
                               f"subs={json.dumps(cheap_subs)}"})
    RESULTS.append({"case": "O1 sub-pass ceiling ordering on the expensive shape",
                    "claimed": False, "expect": "observed",
                    "outcome": json.dumps(dict(sorted(table[priciest].items(),
                                                      key=lambda kv: -kv[1]))),
                    "falsified": False})

    print("\n" + json.dumps({"table": table, "claims": RESULTS}, indent=2, sort_keys=True))
    falsified = [item for item in RESULTS if item["falsified"]]
    print(f"SUMMARY claims={len(RESULTS)} claim_falsified={len(falsified)}")
    for item in falsified:
        print(f"FALSIFIED: {item['case']} -> {item['outcome']}")
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
