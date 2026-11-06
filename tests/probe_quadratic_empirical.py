"""Empirical test of the O(n^2) claim -- because I have been wrong twice already.

`probe_checker_quadratic_lookups.py` found the cause by STATIC analysis: every lookup
helper is a linear scan, and seven checker functions call one inside a loop. Static
analysis can show a quadratic is POSSIBLE; it cannot show it is what actually happens.

This probe tests it at runtime with a prediction the two models make differently.

  If the cost is O(n^2) in the TOTAL node count, then the same number of nodes costs
  the same whether they sit in one function or are split across several -- the scans
  walk the whole node list either way.

  If the cost is O(n) per function (scans bounded by a function's own subtree), then
  splitting the same nodes across two functions should roughly halve the cost, and a
  split program should survive where a single-function one fails.

So: build N nodes in ONE function, and the same N nodes split across TWO functions,
and compare where each hits the ceiling.

Run: python tests/probe_quadratic_empirical.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def one_function(count):
    body = "".join(f"  let a{index} = {index}\n" for index in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def two_functions(count):
    half = count // 2
    first = "".join(f"  let a{index} = {index}\n" for index in range(half))
    second = "".join(f"  let b{index} = {index}\n" for index in range(count - half))
    return (f"fn f() -> Int {{\n{first}  return 0\n}}\n"
            f"fn g() -> Int {{\n{second}  return 0\n}}\n"
            "fn main() -> Int { return f() }\n")


COUNTS = [8, 12, 16, 20, 24, 28, 32, 40]


def measure(session, revision, source, label):
    payload = source.encode("utf-8")
    target = session.send({"schemaVersion": 3, "op": "open_bytes",
                           "name": label, "bytes": list(payload)})
    if target.get("outcome") != "ok":
        return None, "open:" + str((target.get("error") or {}).get("code"))
    semantic = {"document": target["document"], "revision": target["revision"],
                "entryFunctions": []}
    try:
        parsed = parse_target(session, payload, target, revision)
    except Exception as error:  # noqa: BLE001
        text = str(error)
        for code in ("PEP_RUNTIME_STEP_LIMIT", "PEP_TOOL_VALUE_LIMIT",
                     "PEP_SOURCE_BYTE_LIMIT"):
            if code in text:
                return None, "parse:" + code
        return None, "parse-failed"
    nodes = session.parser_measurements.get("parser_node_count")
    try:
        checked = session.send({"schemaVersion": 3, "toolProtocolVersion": 2,
                                "op": "tool_invoke", "tool": "pep-c23-checker",
                                "arguments": [parsed], "semanticTarget": semantic})
    except RuntimeError as error:
        return nodes, "transport:" + str(error)[:40]
    if checked.get("outcome") != "ok":
        return nodes, (checked.get("error") or {}).get("code")
    fields = {f["name"]: f["value"] for f in checked["result"]["fields"]}
    return nodes, fields["status"]["value"]


def main():
    session = Session()
    results = {"one": [], "two": []}
    try:
        bundle = "\n".join(p.read_text(encoding="utf-8") for p in pep_c23.SOURCES)
        opened = session.send({"schemaVersion": 3, "op": "open", "source": bundle,
                               "name": "pep-c23-emitter", "metadataOnly": True})
        require(opened, "outcome", "ok", "open compiler bundle")
        require(opened, "status", "valid", "check compiler bundle")
        document, revision = opened["document"], opened["revision"]
        sample = session.send({"schemaVersion": 3, "op": "open_bytes",
                               "name": "validate", "bytes": []})
        require(sample, "outcome", "ok", "open validation source")

        spec = importlib.util.spec_from_file_location(
            "pic", ROOT / "tests" / "probe_integration_case.py")
        pic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pic)
        pic.register(session, document, revision, sample["document"], sample["revision"])

        for label, builder in (("one", one_function), ("two", two_functions)):
            print(f"\n{label} function(s):")
            for count in COUNTS:
                source = builder(count)
                nodes, outcome = measure(session, revision, source,
                                         f"quad-{label}-{count}")
                print(f"  units={count:3d} nodes={str(nodes):>5} -> {outcome}")
                results[label].append((count, nodes, outcome))
                if outcome != "valid":
                    break
    finally:
        session.close()

    def largest_ok(key):
        best = None
        for count, nodes, outcome in results[key]:
            if outcome == "valid":
                best = (count, nodes)
        return best

    one = largest_ok("one")
    two = largest_ok("two")
    print(f"\nlargest accepted: one-function={one}  two-function={two}")
    if one and two:
        one_nodes = one[1] or 0
        two_nodes = two[1] or 0
        if two_nodes <= one_nodes * 1.25:
            print("\nCONSISTENT WITH O(n^2) IN TOTAL NODES: splitting across functions "
                  "does not buy headroom.")
        else:
            print("\nNOT CONSISTENT WITH GLOBAL O(n^2): splitting bought headroom, so "
                  "the scans are bounded per function.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
