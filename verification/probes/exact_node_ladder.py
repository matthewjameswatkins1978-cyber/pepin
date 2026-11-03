"""Exact node ladder — how many nodes does the Pep-written checker actually afford?

The axis probe reported brackets (60 ok / 64 refused). This probe narrows the boundary
to individual node counts on the frozen 66-node row's family (a boolean-chain function
over Int comparisons plus trailing `let` statements for fine adjustment), then states
what the remaining gap requires in nodes and in per-node headroom.

Generator: `fn f(x: Int) -> Bool { return <k-term chain> }` plus `l` top-level
`let` statements, which lets the node count be tuned in steps of 2 rather than 4.

Claims:
  N1  a last-passing and a first-failing node count are both found (a real boundary).
  N2  the boundary sits at or below 66 nodes on the A1 head — i.e. the frozen 66-node
      row is at most a few nodes past a measured cliff, not an order of magnitude.
  N3  the implied headroom is stated as a number: nodes_needed / nodes_available,
      and steps needed at the measured per-node upper bound (100_000 / last_pass).

Exit codes: 0 = ladder produced and claims held, 1 = a claim falsified, 2 = harness error.
Usage: python exact_node_ladder.py <tree-with-checker> [max_nodes]
"""
import json
import pathlib
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_NODES = int(sys.argv[2]) if len(sys.argv) > 2 else 72
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

BUDGET = 100_000


def program(terms: int, lets: int) -> bytes:
    chain = " && ".join(f"x == {index}" for index in range(terms))
    body = [f"let g{index} = {index};" for index in range(lets)]
    body.append(f"fn f(x: Int) -> Bool {{\n  return {chain}\n}}")
    body.append("fn main() -> Int { return 0 }")
    return ("\n\n".join(body) + "\n").encode()


def main():
    print(f"REPO={REPO}")
    session = Session()
    rows = []
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-exact-bundle", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        sample = session.send({"schemaVersion": 3, "op": "open_bytes", "name": "v",
                               "bytes": []})
        target_spec = {"document": sample["document"], "revision": sample["revision"],
                       "entryFunctions": []}
        start_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"])
        finished_cursor = pep_c23.parser_cursor_value(sample["document"], sample["revision"],
                                                     done=True, lex_done=True,
                                                     lex_stage="done")
        empty = pep_c23.parser_progress(sample["document"], sample["revision"])
        for tool, function, arguments, expect in [
                ("pep-c23-parser-start", "parser_start", [], start_cursor),
                ("pep-c23-parser-step", "parser_step", [finished_cursor],
                 pep_c23.parser_chunk_value(sample["document"], sample["revision"],
                                            finished_cursor)),
                ("pep-c23-checker", "analyze_parsed", [empty],
                 pep_c23.checker_report(sample["document"], sample["revision"]))]:
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2, "op": "tool_register",
                          "tool": tool, "document": opened["document"],
                          "revision": opened["revision"], "function": function})
            validated = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                      "op": "tool_validate", "tool": tool,
                                      "document": opened["document"],
                                      "revision": opened["revision"],
                                      "testVectors": [{"arguments": arguments,
                                                       "expect": expect,
                                                       "semanticTarget": target_spec}]})
            require(validated, "status", "Validated", f"validate {tool}")
            session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                          "op": "tool_activate", "tool": tool,
                          "document": opened["document"],
                          "revision": opened["revision"]})

        seen = {}
        for terms in range(2, 24):
            for lets in (0, 1, 2, 3):
                source = program(terms, lets)
                target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": f"a3-exact-{terms}-{lets}",
                                       "bytes": list(source)})
                require(target, "outcome", "ok", "open payload")
                try:
                    parsed = parse_target(session, source, target, opened["revision"])
                except BaseException:  # noqa: BLE001 - parser budget is data here
                    continue
                nodes = 0
                for field in parsed["fields"]:
                    if field["name"] == "nodes":
                        nodes = len(field["value"]["value"])
                if nodes in seen or nodes > MAX_NODES:
                    continue
                response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke", "tool": "pep-c23-checker",
                                         "arguments": [parsed],
                                         "semanticTarget": {"document": target["document"],
                                                            "revision": target["revision"],
                                                            "entryFunctions": []}})
                state = ("ok" if response.get("outcome") == "ok"
                         else (response.get("error") or {}).get("code"))
                seen[nodes] = {"nodes": nodes, "terms": terms, "lets": lets,
                               "bytes": len(source), "state": state}
    finally:
        session.close()

    for nodes in sorted(seen):
        row = seen[nodes]
        rows.append(row)
        print(f"nodes={nodes:>3} bytes={row['bytes']:>4} terms={row['terms']:>2} "
              f"lets={row['lets']} state={row['state']}")

    passing = [row for row in rows if row["state"] == "ok"]
    failing = [row for row in rows if row["state"] != "ok"]
    last_pass = max((row["nodes"] for row in passing), default=None)
    first_fail = min((row["nodes"] for row in failing), default=None)
    results = []
    results.append({"case": "N1 a boundary with both sides observed", "claimed": True,
                    "expect": "both found",
                    "falsified": not (last_pass is not None and first_fail is not None),
                    "outcome": f"last_pass={last_pass} first_fail={first_fail}"})
    results.append({"case": "N2 boundary at or below 66 nodes", "claimed": True,
                    "expect": "<=66", "falsified": not (first_fail is not None
                                                        and first_fail <= 66),
                    "outcome": f"first_fail={first_fail}"})
    if last_pass:
        per_node = BUDGET / last_pass
        needed = per_node * 66
        results.append({"case": "N3 headroom stated as numbers", "claimed": False,
                        "expect": "observed",
                        "outcome": f"per_node_upper_bound={per_node:.0f} steps; "
                                   f"66 nodes needs <={needed:.0f} steps vs {BUDGET} "
                                   f"budget ({(needed / BUDGET - 1) * 100:.0f}% over)",
                        "falsified": False})
        print(f"\nlast passing node count: {last_pass}; first failing: {first_fail}")
        print(f"per-node upper bound: {per_node:.0f} steps (100k / {last_pass})")
        print(f"66 nodes would need <={needed:.0f} steps "
              f"({(needed / BUDGET - 1) * 100:.0f}% over the {BUDGET} budget)")
    print("\n" + json.dumps({"rows": rows, "claims": results}, indent=2, sort_keys=True))
    falsified = [item for item in results if item["falsified"]]
    print(f"SUMMARY claims={len(results)} claim_falsified={len(falsified)}")
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
