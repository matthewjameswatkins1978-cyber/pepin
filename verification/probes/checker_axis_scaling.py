"""Does the whole-checker cost scale with expression DEPTH or with NODE COUNT?

The cost profile and pass attribution put the expensive shapes' cost inside
`analyze_parsed`. This probe separates two candidate drivers using one shape family
(the boolean-chain family, where the frozen 66-node fixture lives) varied along one
axis at a time:

  breadth  `x == 0 && x == 1 && … && x == k`      — nodes grow, nesting depth stays 2
  depth    `x == 0 && (x == 1 || (x == 2 && …))`  — nodes grow with nesting depth

For each axis the ladder records parse nodes and whether `analyze_parsed` completes
under the fixed 100,000-step budget, then compares the node count at the ceiling:

  D1  breadth has a measurable ceiling and it is higher than 2 nodes.
  D2  depth has a measurable ceiling.
  D3  depth is the binding axis: nodes-at-ceiling for depth is at least 1.5x lower
      than for breadth. (If the ratio is ~1, cost is node-driven, not depth-driven,
      and that is what will be reported.)

Exit codes: 0 = curves produced and claims held, 1 = a claim falsified,
2 = harness error.
Usage: python checker_axis_scaling.py <tree-with-checker> [max_rung]
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
MAX_RUNG = int(sys.argv[2]) if len(sys.argv) > 2 else 24
sys.path.insert(0, str(REPO))

import pep_c23  # noqa: E402
from pep_c23 import Session, parse_target, require  # noqa: E402

PEP_PS1 = REPO / "pep.ps1"


def breadth(k: int) -> bytes:
    terms = " && ".join(f"x == {index}" for index in range(k + 1))
    return f"fn f(x: Int) -> Bool {{\n  return {terms}\n}}\n\nfn main() -> Int {{ return 0 }}\n".encode()


def depth(d: int) -> bytes:
    """Alternating `&&` / `||` nesting, d levels deep, valid Pep."""
    expression = "x == 0"
    for level in range(1, d + 1):
        operator = "&&" if level % 2 else "||"
        expression = f"x == {level} {operator} ({expression})"
    return (f"fn f(x: Int) -> Bool {{\n  return {expression}\n}}\n\n"
            f"fn main() -> Int {{ return 0 }}\n").encode()


def seed_status(source: bytes):
    import tempfile
    with tempfile.TemporaryDirectory(prefix="a3-axis-") as folder:
        path = pathlib.Path(folder) / "probe.pep"
        path.write_bytes(source)
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
    curves = {}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "a3-axis-bundle", "metadataOnly": True})
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

        for axis, generator in (("breadth", breadth), ("depth", depth)):
            rows = []
            for rung in range(1, MAX_RUNG + 1):
                source = generator(rung)
                target = session.send({"schemaVersion": 3, "op": "open_bytes",
                                       "name": f"a3-axis-{axis}-{rung}",
                                       "bytes": list(source)})
                require(target, "outcome", "ok", "open payload")
                try:
                    parsed = parse_target(session, source, target, opened["revision"])
                except BaseException as error:  # noqa: BLE001
                    rows.append({"rung": rung, "bytes": len(source), "nodes": None,
                                 "state": f"PARSE:{str(error)[:40]}"})
                    print(f"{axis:<8} rung={rung:>3} bytes={len(source):>5} "
                          f"nodes=? state=PARSE")
                    continue
                nodes = 0
                for field in parsed["fields"]:
                    if field["name"] == "nodes":
                        nodes = len(field["value"]["value"])
                response = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                         "op": "tool_invoke", "tool": "pep-c23-checker",
                                         "arguments": [parsed],
                                         "semanticTarget": {"document": target["document"],
                                                            "revision": target["revision"],
                                                            "entryFunctions": []}})
                state = ("ok" if response.get("outcome") == "ok"
                         else (response.get("error") or {}).get("code"))
                rows.append({"rung": rung, "bytes": len(source), "nodes": nodes,
                             "state": state})
                print(f"{axis:<8} rung={rung:>3} bytes={len(source):>5} nodes={nodes:>4} "
                      f"state={state}")
            curves[axis] = rows
    finally:
        session.close()

    summary = {}
    for axis, rows in curves.items():
        ok = [row for row in rows if row["state"] == "ok"]
        bad = [row for row in rows if row["state"] != "ok"]
        last = max(ok, key=lambda row: row["rung"]) if ok else None
        first_bad = bad[0] if bad else None
        summary[axis] = {"last_ok": last, "first_bad": first_bad}
        print(f"\n{axis}: last ok rung={last['rung'] if last else '-'} "
              f"nodes={last['nodes'] if last else '-'} "
              f"({last['bytes'] if last else '-'} B); first refusal "
              f"{first_bad['state'] + ' at rung ' + str(first_bad['rung']) + ' nodes=' + str(first_bad['nodes']) if first_bad else '-'}")

    RESULTS = []
    breadth_nodes = summary["breadth"]["last_ok"]["nodes"] if summary["breadth"]["last_ok"] else 0
    depth_nodes = summary["depth"]["last_ok"]["nodes"] if summary["depth"]["last_ok"] else 0
    RESULTS.append({"case": "D1 breadth has a measurable ceiling above 2 nodes",
                    "claimed": True, "expect": ">2",
                    "falsified": not (summary["breadth"]["first_bad"] and breadth_nodes > 2),
                    "outcome": f"breadth nodes={breadth_nodes}, "
                               f"refused={bool(summary['breadth']['first_bad'])}"})
    RESULTS.append({"case": "D2 depth has a measurable ceiling", "claimed": True,
                    "expect": "measured",
                    "falsified": summary["depth"]["first_bad"] is None,
                    "outcome": f"depth nodes={depth_nodes}"})
    ratio = breadth_nodes / max(depth_nodes, 1)
    RESULTS.append({"case": "D3 depth is the binding axis (breadth ceiling >=1.5x depth)",
                    "claimed": True, "expect": "ratio>=1.5", "falsified": ratio < 1.5,
                    "outcome": f"breadth={breadth_nodes} depth={depth_nodes} "
                               f"ratio={ratio:.2f}"})

    observations = []
    for axis in ("breadth", "depth"):
        first_bad = summary[axis]["first_bad"]
        if first_bad:
            observations.append({axis: first_bad["rung"],
                                 "seed": seed_status((breadth if axis == "breadth"
                                                      else depth)(first_bad["rung"]))})
    RESULTS.append({"case": "O1 refused rungs are seed-valid", "claimed": False,
                    "expect": "observed", "outcome": json.dumps(observations),
                    "falsified": False})

    print("\n" + json.dumps({"summary": {axis: {"last_ok": summary[axis]["last_ok"],
                                                "first_bad": summary[axis]["first_bad"]}
                                          for axis in summary},
                             "claims": RESULTS}, indent=2, sort_keys=True, default=str))
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
