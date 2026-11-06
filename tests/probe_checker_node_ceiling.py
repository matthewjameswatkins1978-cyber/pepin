"""Confirm the corrected model: is the checker's ceiling a constant NODE COUNT?

I got this wrong once. `probe_checker_cost_shape.py` concluded "per-byte,
shape-independent" from four constructs that happened to share a node density.
`probe_checker_cost_driver.py` then showed a 691-byte few-node program passing where a
371-byte many-node program failed, which points at node count instead.

A single pair is not a model. This probe measures the ACTUAL node count of each
program (the parser reports it) and asks whether the ceiling is a constant node
budget across very different node densities. If it is, the model is confirmed and A1
has a precise unit to design against. If it is not, the model is wrong again and I
want to know before anyone builds on it.

Run: python tests/probe_checker_node_ceiling.py
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_build"))

import pep_c23  # noqa: E402
from pep_c23 import Session, require, parse_target  # noqa: E402


def dense(count):
    """Many short statements: high node density."""
    body = "".join(f"  let a{index} = {index}\n" for index in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def sparse(count):
    """Few long string literals: low node density, many bytes."""
    body = "".join(f'  say("{"x" * 80}")\n' for _ in range(count))
    return f"fn f() -> Int {{\n{body}  return 0\n}}\nfn main() -> Int {{ return f() }}\n"


def medium(count):
    """Function calls: intermediate density."""
    body = "".join(f"  let r{index} = g({index})\n" for index in range(count))
    return ("fn g(n: Int) -> Int { return n }\n"
            f"fn f() -> Int {{\n{body}  return 0\n}}\n"
            "fn main() -> Int { return f() }\n")


SHAPES = {"dense": dense, "medium": medium, "sparse": sparse}
COUNTS = [2, 4, 6, 8, 10, 12, 16, 20, 24, 32]


def measure(session, revision, source, label):
    """Return (node_count, outcome)."""
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
    ceilings = {}
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

        for shape, builder in SHAPES.items():
            print(f"\n{shape}:")
            largest_ok_nodes = None
            for count in COUNTS:
                source = builder(count)
                nodes, outcome = measure(session, revision, source,
                                         f"{shape}-{count}")
                size = len(source.encode("utf-8"))
                print(f"  units={count:3d} bytes={size:5d} nodes={str(nodes):>5} "
                      f"-> {outcome}")
                if outcome == "valid":
                    largest_ok_nodes = nodes
                else:
                    break
            ceilings[shape] = largest_ok_nodes
    finally:
        session.close()

    print("\nlargest node count accepted, by shape:")
    for shape, nodes in ceilings.items():
        print(f"  {shape:8s} {nodes}")
    values = [v for v in ceilings.values() if v]
    if len(values) >= 2 and max(values) - min(values) <= max(2, min(values) // 4):
        print("\nCONFIRMED: the ceiling is a roughly constant NODE COUNT across "
              "densities.")
    else:
        print("\nNOT CONFIRMED: the node ceiling varies with shape, so node count "
              "alone does not explain the cost.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
